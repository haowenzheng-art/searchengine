"""Pytest 配置和公共 fixtures.

所有 fixture 都是 function-scoped 避免 asyncpg 跨 event loop 问题.
"""
from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/wda"


@pytest_asyncio.fixture
async def test_engine():
    """每个测试函数独立 engine (asyncpg 绑定 event loop，不能跨 loop 复用)."""
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(test_engine):
    """每个测试函数独立 session factory."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory


@pytest_asyncio.fixture
async def db_session(session_factory):
    """给测试查询用的独立 session."""
    async with session_factory() as session:
        yield session


class MockLLMResponse:
    """模拟 Anthropic SDK 的 LLMResponse."""

    def __init__(
        self,
        content: list[dict[str, Any]],
        stop_reason: str = "end_turn",
        input_tokens: int = 100,
        output_tokens: int = 50,
    ):
        self.content = content
        self.stop_reason = stop_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = "mock-model"


class MockLLMClient:
    """模拟 LLMClient - 按预设脚本返回响应."""

    def __init__(self, responses: list[MockLLMResponse]):
        self.responses = list(responses)
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    async def create_message(self, messages, **kwargs):
        if self.call_count >= len(self.responses):
            raise RuntimeError(
                f"MockLLMClient exhausted: call {self.call_count + 1} but only {len(self.responses)} responses"
            )
        self.calls.append({"messages": messages, "kwargs": kwargs})
        response = self.responses[self.call_count]
        self.call_count += 1
        return response

    async def stream_message(self, *args, **kwargs):
        raise NotImplementedError("mock does not support streaming")


def make_tool_use_block(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str | None = None,
) -> dict[str, Any]:
    return {
        "type": "tool_use",
        "id": tool_use_id or f"toolu_mock_{tool_name}",
        "name": tool_name,
        "input": tool_input,
    }


def make_text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


@pytest.fixture
def mock_llm():
    def _factory(responses):
        return MockLLMClient(responses)
    return _factory
