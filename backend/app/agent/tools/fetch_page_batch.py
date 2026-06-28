"""fetch_page_batch tool - 批量抓取多个 URL 页面正文.

把串行的 6 次抓取变成一次 tool call 内部并发，减少 orchestrator 迭代数。
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent.context import get_workflow_id
from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.evidence import Evidence
from app.search.fetcher import fetch_page as _fetch_page

log = get_logger(__name__)

# Playwright 并发上限 - 开太多浏览器页会爆内存/CPU
_MAX_CONCURRENT_FETCHES = 5


class FetchPageBatchInput(ToolInput):
    urls: list[str]


class FetchPageBatchItemOutput(BaseModel):
    url: str
    word_count: int = Field(ge=0)
    fetch_time_ms: int = Field(ge=0)
    title: str | None = None
    error: str | None = None
    # content 不返回给 orchestrator，避免消息上下文爆炸；已写入 evidence 表


class FetchPageBatchOutput(ToolOutput):
    results: list[FetchPageBatchItemOutput]


async def _persist_fetch(
    workflow_id: int,
    url: str,
    title: str | None,
    content: str,
    word_count: int,
) -> None:
    """把抓取到的正文写入 evidence 表；已存在则更新."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Evidence).where(
                Evidence.workflow_id == workflow_id,
                Evidence.url == url,
            )
        )
        ev = result.scalar_one_or_none()
        if ev is None:
            ev = Evidence(workflow_id=workflow_id, url=url, title=title)
            session.add(ev)

        ev.title = title or ev.title
        ev.content = content
        ev.word_count = word_count
        ev.fetched_at = datetime.utcnow()
        await session.commit()


async def _fetch_one(url: str, workflow_id: int | None) -> FetchPageBatchItemOutput:
    result = await _fetch_page(url)
    if workflow_id is not None and result.error is None:
        await _persist_fetch(
            workflow_id=workflow_id,
            url=result.url,
            title=result.title,
            content=result.content,
            word_count=result.word_count,
        )
    return FetchPageBatchItemOutput(
        url=result.url,
        word_count=result.word_count,
        fetch_time_ms=result.fetch_time_ms,
        title=result.title,
        error=result.error,
    )


class FetchPageBatchTool(Tool):
    name = "fetch_page_batch"
    description = (
        "批量抓取多个 URL 的页面正文. "
        "在 score_evidence_batch 之后调用，只抓 score >= 7 的 URL. "
        "返回每个 URL 的字数、标题、抓取耗时；正文写入 evidence 表，不返回给 orchestrator."
    )
    input_schema = FetchPageBatchInput
    output_schema = FetchPageBatchOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, FetchPageBatchInput)
        log.info("fetch_page_batch_called", url_count=len(input.urls))
        workflow_id = get_workflow_id()

        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

        async def _bounded(url: str) -> FetchPageBatchItemOutput:
            async with semaphore:
                return await _fetch_one(url, workflow_id)

        results = await asyncio.gather(*[_bounded(url) for url in input.urls])
        log.info("fetch_page_batch_done", url_count=len(results))
        return FetchPageBatchOutput(results=results)

