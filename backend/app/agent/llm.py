"""LLM 客户端封装 - 支持 Anthropic 和 OpenAI 两种协议.

设计原则:
1. 不静默 fallback - 失败就抛异常
2. 多 provider 兼容 - Anthropic SDK (Claude/Volc) + OpenAI SDK (Agnes/ChatGPT)
3. 内部统一用 Anthropic 格式的 content block, orchestrator 和 tools 无感切换
4. tool use 透传 - 工具调用由 orchestrator 处理
5. token 持久化 - 返回 input/output tokens 用于计费和审计
"""
from __future__ import annotations

import contextvars
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent
from openai import AsyncOpenAI

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


# Contextvar - 让 orchestrator 注入 LLMClient，tool 内部能取到同一个实例.
_current_llm: contextvars.ContextVar["LLMClient | None"] = contextvars.ContextVar(
    "_current_llm", default=None
)


def set_current_llm(llm: "LLMClient | None") -> contextvars.Token["LLMClient | None"]:
    """设置当前上下文的 LLMClient，返回 token 用于恢复."""
    return _current_llm.set(llm)


def reset_current_llm(token: contextvars.Token["LLMClient | None"]) -> None:
    """恢复 contextvar 到 set 之前的状态."""
    _current_llm.reset(token)


def get_current_llm() -> "LLMClient":
    """获取当前上下文的 LLMClient，没设置则返回单例."""
    llm = _current_llm.get()
    if llm is not None:
        return llm
    return LLMClient.get()


@dataclass
class LLMResponse:
    """标准化的 LLM 响应包装（内部统一成 Anthropic content block 格式）."""
    content: list[dict[str, Any]]
    stop_reason: str | None
    input_tokens: int
    output_tokens: int
    model: str
    raw: Any


class LLMClient:
    """异步 LLM 客户端封装，根据 settings.llm_provider 自动选择后端."""

    _instance: LLMClient | None = None

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        if self.provider == "openai":
            if not settings.openai_api_key:
                log.warning("openai_api_key_not_set", msg="LLM calls will fail at runtime")
            self._openai = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
            self._models = {
                "haiku": settings.openai_model,
                "sonnet": settings.openai_model,
                "opus": settings.openai_model,
            }
        else:
            key = settings.llm_api_key or settings.anthropic_api_key
            if not key:
                log.warning("anthropic_api_key_not_set", msg="LLM calls will fail at runtime")
            self._anthropic = AsyncAnthropic(
                api_key=key,
                base_url=settings.llm_base_url,
            )
            self._models = {
                "haiku": settings.llm_model or settings.anthropic_model_haiku,
                "sonnet": settings.llm_model or settings.anthropic_model_sonnet,
                "opus": settings.llm_model or settings.anthropic_model_opus,
            }

    @classmethod
    def get(cls) -> LLMClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def resolve_model(self, tier: str) -> str:
        if tier not in self._models:
            raise ValueError(f"unknown model tier: {tier}, expected haiku/sonnet/opus")
        return self._models[tier]

    async def create_message(
        self,
        messages: list[dict[str, Any]],
        *,
        tier: str = "sonnet",
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """非流式调用，返回完整 message."""
        if self.provider == "openai":
            return await self._create_message_openai(
                messages,
                tier=tier,
                system=system,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        return await self._create_message_anthropic(
            messages,
            tier=tier,
            system=system,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _create_message_anthropic(
        self,
        messages: list[dict[str, Any]],
        *,
        tier: str,
        system: str | None,
        tools: list[dict[str, Any]] | None,
        tool_choice: dict[str, Any] | None,
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        model = self.resolve_model(tier)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or settings.agent_max_tokens_per_call,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        log.info(
            "llm_call_start",
            provider="anthropic",
            model=model,
            tier=tier,
            message_count=len(messages),
            has_tools=bool(tools),
            temperature=temperature,
        )
        try:
            response: Message = await self._anthropic.messages.create(**kwargs)
        except Exception as e:
            log.error("llm_call_failed", provider="anthropic", model=model, tier=tier, error=str(e))
            raise

        log.info(
            "llm_call_done",
            provider="anthropic",
            model=response.model,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return LLMResponse(
            content=[block.model_dump() for block in response.content],
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            raw=response,
        )

    async def _create_message_openai(
        self,
        messages: list[dict[str, Any]],
        *,
        tier: str,
        system: str | None,
        tools: list[dict[str, Any]] | None,
        tool_choice: dict[str, Any] | None,
        temperature: float,
        max_tokens: int | None,
    ) -> LLMResponse:
        model = self.resolve_model(tier)
        openai_messages = _anthropic_messages_to_openai(messages)
        if system:
            openai_messages.insert(0, {"role": "system", "content": system})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_tokens": max_tokens or settings.agent_max_tokens_per_call,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = [_anthropic_tool_to_openai(t) for t in tools]
            kwargs["tool_choice"] = _anthropic_tool_choice_to_openai(tool_choice)

        log.info(
            "llm_call_start",
            provider="openai",
            model=model,
            tier=tier,
            message_count=len(messages),
            has_tools=bool(tools),
            temperature=temperature,
        )
        try:
            response = await self._openai.chat.completions.create(**kwargs)
        except Exception as e:
            log.error("llm_call_failed", provider="openai", model=model, tier=tier, error=str(e))
            raise

        content, stop_reason = _openai_response_to_anthropic(response)
        log.info(
            "llm_call_done",
            provider="openai",
            model=response.model,
            stop_reason=stop_reason,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )
        return LLMResponse(
            content=content,
            stop_reason=stop_reason,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=response.model or model,
            raw=response,
        )

    async def stream_message(
        self,
        messages: list[dict[str, Any]],
        *,
        tier: str = "opus",
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> AsyncIterator[MessageStreamEvent]:
        """流式调用，yield 每个事件.

        当前只支持 Anthropic provider；OpenAI 流式可后续扩展.
        """
        if self.provider == "openai":
            raise NotImplementedError("stream_message for OpenAI provider is not implemented yet")
        model = self.resolve_model(tier)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or settings.agent_max_tokens_per_call,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        log.info("llm_stream_start", provider="anthropic", model=model, tier=tier, message_count=len(messages))
        async with self._anthropic.messages.stream(**kwargs) as stream:
            async for event in stream:
                yield event


# ===== 协议转换函数 =====

def _anthropic_tool_to_openai(tool: dict[str, Any]) -> dict[str, Any]:
    """Anthropic tool schema -> OpenAI function schema."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _anthropic_tool_choice_to_openai(tool_choice: dict[str, Any] | None) -> Any:
    """Anthropic tool_choice -> OpenAI tool_choice."""
    if tool_choice is None:
        return "auto"
    tc_type = tool_choice.get("type")
    if tc_type == "tool":
        return {"type": "function", "function": {"name": tool_choice["name"]}}
    if tc_type == "any":
        return "required"
    if tc_type == "auto":
        return "auto"
    return "auto"


def _anthropic_messages_to_openai(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把 orchestrator 内部使用的 Anthropic 格式消息转成 OpenAI 格式.

    Anthropic 角色: user / assistant
    Anthropic content block:
      - text: {"type": "text", "text": "..."}
      - tool_use: {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
      - tool_result: {"type": "tool_result", "tool_use_id": "...", "content": "..."}

    OpenAI 角色: system / user / assistant / tool
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "assistant":
            if isinstance(content, str):
                out.append({"role": "assistant", "content": content})
            else:
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                            },
                        })
                out.append({
                    "role": "assistant",
                    "content": "\n".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls if tool_calls else None,
                })
        elif role == "user":
            # user 消息里可能混合 text 和 tool_result block，也可能是简单字符串
            if isinstance(content, str):
                if content:
                    out.append({"role": "user", "content": content})
            else:
                text_parts: list[str] = []
                tool_results: list[dict[str, Any]] = []
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        tool_results.append(block)
                if text_parts:
                    out.append({"role": "user", "content": "\n".join(text_parts)})
                for tr in tool_results:
                    out.append({
                        "role": "tool",
                        "tool_call_id": tr["tool_use_id"],
                        "content": _tool_result_content_to_str(tr.get("content")),
                    })
        else:
            # 其他角色原样传递（理论上不会有）
            out.append(msg)
    return out


def _tool_result_content_to_str(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _decode_json_strings(obj: Any) -> Any:
    """递归地把字符串化的 JSON 数组/对象解码成真正的 Python 对象.

    某些 OpenAI 兼容模型（如 Agnes）会把复杂字段二次编码成字符串返回，
    这里做一层容错，避免 pydantic 校验失败.
    """
    if isinstance(obj, dict):
        return {k: _decode_json_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode_json_strings(item) for item in obj]
    if isinstance(obj, str):
        stripped = obj.strip()
        if (stripped.startswith("[") and stripped.endswith("]")) or (
            stripped.startswith("{") and stripped.endswith("}")
        ):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except json.JSONDecodeError:
                pass
    return obj


def _openai_response_to_anthropic(response: Any) -> tuple[list[dict[str, Any]], str | None]:
    """OpenAI chat.completion -> Anthropic content block 列表 + stop_reason."""
    choice = response.choices[0]
    message = choice.message
    content: list[dict[str, Any]] = []

    if message.content:
        content.append({"type": "text", "text": message.content})

    for tc in message.tool_calls or []:
        try:
            input_obj = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            input_obj = {}
        input_obj = _decode_json_strings(input_obj)
        content.append({
            "type": "tool_use",
            "id": tc.id,
            "name": tc.function.name,
            "input": input_obj,
        })

    finish_reason = choice.finish_reason
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "stop":
        stop_reason = "end_turn"
    else:
        stop_reason = finish_reason
    return content, stop_reason
