"""Agent 状态持久化 helper.

封装 agent_runs 和 tool_calls 的 DB 操作，让 orchestrator 专注循环逻辑.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, ToolCall


async def create_agent_run(
    session: AsyncSession, workflow_id: int, query: str
) -> AgentRun:
    """创建新的 agent run，初始 messages 是 user query."""
    agent_run = AgentRun(
        workflow_id=workflow_id,
        status="running",
        messages=[{"role": "user", "content": query}],
        current_iteration=0,
    )
    session.add(agent_run)
    await session.commit()
    await session.refresh(agent_run)
    return agent_run


async def load_agent_run(session: AsyncSession, agent_run_id: int) -> AgentRun:
    agent_run = await session.get(AgentRun, agent_run_id)
    if agent_run is None:
        raise ValueError(f"agent_run not found: {agent_run_id}")
    return agent_run


async def persist_tool_call(
    session: AsyncSession,
    agent_run_id: int,
    *,
    tool_name: str,
    tool_call_id: str,
    iteration: int,
    input_args: dict[str, Any],
    output_result: dict[str, Any] | None,
    error: str | None,
    input_tokens: int,
    output_tokens: int,
    duration_ms: int,
) -> ToolCall:
    """持久化单个 tool call."""
    tool_call = ToolCall(
        agent_run_id=agent_run_id,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        iteration=iteration,
        input_args=input_args,
        output_result=output_result,
        error=error,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
    )
    session.add(tool_call)
    await session.commit()
    return tool_call


async def update_agent_run_state(
    session: AsyncSession,
    agent_run: AgentRun,
    *,
    messages: list[dict[str, Any]],
    current_iteration: int,
    status: str | None = None,
    final_output: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """更新 agent run 的状态.

    注意: 必须用 list(messages) 创建新 list，否则 SQLAlchemy 的 JSONB
    不会检测到原地修改 (agent_run.messages 和 messages 是同一个对象时).
    """
    agent_run.messages = list(messages)
    agent_run.current_iteration = current_iteration
    if status:
        agent_run.status = status
    if final_output is not None:
        agent_run.final_output = dict(final_output) if final_output else final_output
    if error is not None:
        agent_run.error = error
    if status in ("completed", "failed"):
        agent_run.ended_at = datetime.utcnow()
    await session.commit()


async def finalize_agent_run(
    session: AsyncSession,
    agent_run: AgentRun,
    *,
    status: str,
    final_output: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """结束时调用."""
    agent_run.status = status
    agent_run.ended_at = datetime.utcnow()
    if final_output is not None:
        agent_run.final_output = final_output
    if error is not None:
        agent_run.error = error
    await session.commit()


class ToolCallTimer:
    """简单的计时器，记录 tool 执行耗时."""

    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)
