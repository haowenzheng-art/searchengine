"""Anthropic SDK 客户端封装。

设计原则:
1. 不静默 fallback - 失败就抛异常，让上层决定怎么处理 (修 legacy/llm_client.py:160-162)
2. 不硬试 URL 变体 - 用官方 SDK 默认 endpoint (修 legacy/llm_client.py:36-44)
3. 多模型切换 - haiku 粗筛 / sonnet 复评 / opus 报告
4. 流式输出 - 支持 messages.stream 用于实时推送 token
5. tool use 透传 - 工具调用由 orchestrator 处理，client 只负责 API 调用
6. token 持久化 - 返回 input/output tokens 用于计费和审计
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


# Contextvar - 让 orchestrator 注入 LLMClient，tool 内部能取到同一个实例.
# 测试时 mock LLM 注入后，所有 LLM 调用都走 mock.
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
    """Anthropic messages.create 返回的标准化包装."""
    content: list[dict[str, Any]]
    stop_reason: str | None
    input_tokens: int
    output_tokens: int
    model: str
    raw: Message


class LLMClient:
    """异步 Anthropic 客户端封装.

    单例模式 - 复用 httpx 连接池.
    """

    _instance: LLMClient | None = None

    def __init__(self) -> None:
        if not settings.llm_api_key:
            log.warning("llm_api_key_not_set", msg="LLM calls will fail at runtime")
        # 火山引擎方舟 Claude 兼容协议: base_url + api_key
        # 底层是 GLM-5.2, 通过 Anthropic SDK 调用, tool use 协议完全兼容
        self._client = AsyncAnthropic(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        # 三个 tier 都映射到同一个模型 (GLM-5.2)
        # 用 temperature 区分: search/score=0.0, extract/report=0.3
        self._models = {
            "haiku": settings.llm_model,
            "sonnet": settings.llm_model,
            "opus": settings.llm_model,
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
        """非流式调用，返回完整 message.

        用于 tool use 循环 - 必须等完整响应才能解析 tool_calls.
        """
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
            model=model,
            tier=tier,
            message_count=len(messages),
            has_tools=bool(tools),
            temperature=temperature,
        )
        try:
            response = await self._client.messages.create(**kwargs)
        except Exception as e:
            log.error("llm_call_failed", model=model, tier=tier, error=str(e), error_type=type(e).__name__)
            raise

        log.info(
            "llm_call_done",
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

        用于最终报告生成 - 让前端看到 token 实时输出.
        不支持 tool use (流式 tool use 复杂度高，留给 V2).
        """
        model = self.resolve_model(tier)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens or settings.agent_max_tokens_per_call,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        log.info("llm_stream_start", model=model, tier=tier, message_count=len(messages))
        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                yield event
