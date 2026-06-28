"""Agent orchestrator - Anthropic SDK 原生 tool use 主循环.

设计要点:
1. 不静默 fallback - LLM 失败抛异常，tool 失败返回 is_error 给 LLM
2. max_iterations 硬上限 - 防止循环失控烧钱
3. 每个 tool_call 持久化 - 用于调试、审计、计费
4. 断点续跑 - messages 存 JSONB，进程崩了能从 DB 恢复
5. 温度分层 - orchestrator LLM 用 0.3 (决策需要灵活)，tool 内部各自设定
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agent.context import reset_workflow_id, set_workflow_id
from app.agent.llm import LLMClient, LLMResponse, reset_current_llm, set_current_llm
from app.agent.prompts import ORCHESTRATOR_SYSTEM
from app.agent.state import (
    ToolCallTimer,
    create_agent_run,
    finalize_agent_run,
    load_agent_run,
    persist_tool_call,
    update_agent_run_state,
)
from app.agent.tools.base import Tool
from app.agent.tools.registry import ToolRegistry, get_registry
from app.config import settings
from app.core.logging import get_logger
from app.models import AgentRun

log = get_logger(__name__)


class Orchestrator:
    """Agent 主循环.

    用法:
        orch = Orchestrator(session_factory)
        agent_run = await orch.run(query="招聘筛选流程", workflow_id=1)
    """

    def __init__(
        self,
        session_factory: async_sessionmaker,
        *,
        llm: LLMClient | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.llm = llm or LLMClient.get()
        self.registry = registry or get_registry()

    async def run(
        self,
        query: str,
        workflow_id: int,
        *,
        resume_from: int | None = None,
    ) -> AgentRun:
        """启动或恢复 agent 循环.

        Args:
            query: 用户查询，如 "招聘筛选流程"
            workflow_id: workflows 表的主键 ID
            resume_from: 如果传了，从该 agent_run_id 恢复继续

        Returns:
            AgentRun - 最终状态 (completed/failed)
        """
        async with self.session_factory() as session:
            if resume_from is not None:
                agent_run = await load_agent_run(session, resume_from)
                log.info("agent_resume", agent_run_id=agent_run.id, iteration=agent_run.current_iteration)
            else:
                agent_run = await create_agent_run(session, workflow_id, query)
                log.info("agent_start", agent_run_id=agent_run.id, workflow_id=workflow_id, query=query)

            try:
                # 把 llm client 注入到 contextvar，让 tool 内部的 call_llm_for_json 也能拿到
                token = set_current_llm(self.llm)
                try:
                    await self._loop(agent_run, query, session)
                finally:
                    reset_current_llm(token)
            except Exception as e:
                log.error("agent_failed", agent_run_id=agent_run.id, error=str(e), error_type=type(e).__name__)
                await finalize_agent_run(session, agent_run, status="failed", error=str(e))
                raise

            return agent_run

    async def _loop(self, agent_run: AgentRun, query: str, session) -> None:
        """tool use 主循环."""
        messages: list[dict[str, Any]] = list(agent_run.messages)
        system = ORCHESTRATOR_SYSTEM.format(max_iterations=settings.agent_max_iterations)
        max_iter = settings.agent_max_iterations
        final_output: dict[str, Any] | None = None
        last_save_report_output: dict[str, Any] | None = None

        for iteration in range(agent_run.current_iteration, max_iter):
            log.info("agent_iteration", agent_run_id=agent_run.id, iteration=iteration)
            await update_agent_run_state(
                session, agent_run, messages=messages, current_iteration=iteration
            )

            # 如果是最后一次迭代，强制要求 LLM 调用 save_report
            is_last = iteration == max_iter - 1
            tool_choice = (
                {"type": "tool", "name": "save_report"} if is_last else None
            )

            response: LLMResponse = await self.llm.create_message(
                messages=messages,
                tier="sonnet",
                system=system,
                tools=self.registry.to_anthropic(),
                temperature=0.3,
                tool_choice=tool_choice,
            )

            # 累加 tokens 到 agent_run (用于计费)
            # 注意：每个 tool 内部的 LLM 调用 token 单独记在 tool_calls 表
            # 这里只记 orchestrator LLM 的 token

            # 把 assistant 响应加到 messages
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                log.info("agent_end_turn", agent_run_id=agent_run.id, iteration=iteration)
                break

            if response.stop_reason != "tool_use":
                log.warning(
                    "agent_unexpected_stop",
                    agent_run_id=agent_run.id,
                    stop_reason=response.stop_reason,
                )
                break

            # 执行所有 tool_use 块
            tool_results = []
            for block in response.content:
                if block.get("type") != "tool_use":
                    continue
                result, save_output = await self._execute_tool(
                    block, agent_run, iteration, response, session
                )
                tool_results.append(result)
                if save_output is not None:
                    last_save_report_output = save_output

            # 把 tool_results 加到 messages (user role)
            messages.append({"role": "user", "content": tool_results})

            # 如果 save_report 已调用，提取 final_output 并结束
            if last_save_report_output is not None:
                final_output = last_save_report_output
                log.info("agent_save_report_done", agent_run_id=agent_run.id, iteration=iteration)
                break

        if final_output is None:
            log.warning(
                "agent_no_save_report",
                agent_run_id=agent_run.id,
                iterations_used=agent_run.current_iteration + 1,
            )

        await finalize_agent_run(
            session,
            agent_run,
            status="completed" if final_output is not None else "failed",
            final_output=final_output,
            error=None if final_output is not None else "agent did not call save_report within max_iterations",
        )
        await update_agent_run_state(
            session, agent_run, messages=messages, current_iteration=agent_run.current_iteration + 1
        )

    async def _execute_tool(
        self,
        tool_use_block: dict[str, Any],
        agent_run: AgentRun,
        iteration: int,
        llm_response: LLMResponse,
        session,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """执行单个 tool_use 块，持久化 tool_call.

        Returns:
            (tool_result_dict_for_next_message, save_report_output_if_any)
        """
        tool_name = tool_use_block["name"]
        tool_use_id = tool_use_block["id"]
        raw_input = tool_use_block["input"]

        log.info(
            "tool_call_start",
            agent_run_id=agent_run.id,
            tool=tool_name,
            iteration=iteration,
        )

        timer = ToolCallTimer()
        error: str | None = None
        output_obj = None
        save_output: dict[str, Any] | None = None

        wf_token = set_workflow_id(agent_run.workflow_id)
        try:
            tool: Tool = self.registry.get(tool_name)
            input_obj = tool.validate_input(raw_input)
            output_obj = await tool.execute(input_obj)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            log.error(
                "tool_call_failed",
                agent_run_id=agent_run.id,
                tool=tool_name,
                error=error,
            )
        finally:
            reset_workflow_id(wf_token)

        duration_ms = timer.elapsed_ms()

        # 持久化 tool_call (无论成功失败)
        output_result = tool.serialize_output(output_obj) if output_obj is not None else None
        await persist_tool_call(
            session,
            agent_run.id,
            tool_name=tool_name,
            tool_call_id=tool_use_id,
            iteration=iteration,
            input_args=raw_input,
            output_result=output_result,
            error=error,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            duration_ms=duration_ms,
        )

        # 构造 tool_result 给 LLM
        if error is not None:
            tool_result_content = json.dumps({"error": error}, ensure_ascii=False)
        else:
            tool_result_content = json.dumps(output_result, ensure_ascii=False)
            # 如果是 save_report，提取输出作为 final_output 候选
            if tool_name == "save_report":
                save_output = output_result

        log.info(
            "tool_call_done",
            agent_run_id=agent_run.id,
            tool=tool_name,
            iteration=iteration,
            duration_ms=duration_ms,
            success=error is None,
        )

        result_dict = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": tool_result_content,
        }
        if error is not None:
            result_dict["is_error"] = True

        return result_dict, save_output
