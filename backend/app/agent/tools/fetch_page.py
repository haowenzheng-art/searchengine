"""fetch_page tool - Playwright 抓取页面正文.

Phase 2: 用真实 fetcher (Playwright + BS4 fallback).
失败时把 error 信息返回给 LLM, LLM 会跳过这个 URL 抓下一个.
"""
from __future__ import annotations

from pydantic import Field

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger
from app.search.fetcher import fetch_page as _fetch_page

log = get_logger(__name__)


class FetchPageInput(ToolInput):
    url: str


class FetchPageOutput(ToolOutput):
    url: str
    content: str
    word_count: int = Field(ge=0)
    fetch_time_ms: int = Field(ge=0)
    title: str | None = None
    error: str | None = None


class FetchPageTool(Tool):
    name = "fetch_page"
    description = (
        "抓取指定 URL 的页面正文. "
        "返回正文内容、字数、抓取耗时. "
        "只对 score >= 7 的 URL 调用，避免浪费."
    )
    input_schema = FetchPageInput
    output_schema = FetchPageOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, FetchPageInput)
        log.info("fetch_page_called", url=input.url)
        result = await _fetch_page(input.url)
        return FetchPageOutput(
            url=result.url,
            content=result.content,
            word_count=result.word_count,
            fetch_time_ms=result.fetch_time_ms,
            title=result.title,
            error=result.error,
        )

