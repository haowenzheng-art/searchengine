"""score_evidence_batch tool - 批量评估多个 URL 与 query 的相关度.

把串行的 6 次评分变成一次 tool call 内部并行，减少 orchestrator 迭代数。
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent.context import get_workflow_id
from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.agent.tools.score_evidence import ScoreEvidenceOutput
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.evidence import Evidence
from app.search.scorer import score_evidence as _score_evidence

log = get_logger(__name__)

# 同时评分的并发数上限 - 避免一次性打爆 LLM provider
_MAX_CONCURRENT_SCORES = 5


class ScoreEvidenceItem(BaseModel):
    url: str
    snippet: str
    title: str | None = None


class ScoreEvidenceBatchInput(ToolInput):
    query: str
    items: list[ScoreEvidenceItem]


class ScoreEvidenceBatchItemOutput(ScoreEvidenceOutput):
    url: str


class ScoreEvidenceBatchOutput(ToolOutput):
    results: list[ScoreEvidenceBatchItemOutput]


async def _persist_score(
    workflow_id: int,
    url: str,
    title: str | None,
    snippet: str,
    score: float,
    reason: str,
    is_homepage: bool,
    is_disambiguation: bool,
    score_layer: int,
) -> None:
    """把评分结果写入 evidence 表；已存在则更新."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Evidence).where(
                Evidence.workflow_id == workflow_id,
                Evidence.url == url,
            )
        )
        ev = result.scalar_one_or_none()
        if ev is None:
            ev = Evidence(
                workflow_id=workflow_id,
                url=url,
                title=title,
                snippet=snippet,
            )
            session.add(ev)

        ev.score = score
        ev.score_reason = reason
        ev.is_homepage = is_homepage
        ev.is_disambiguation = is_disambiguation
        ev.score_layer = score_layer
        await session.commit()


async def _score_one(
    query: str,
    item: ScoreEvidenceItem,
    workflow_id: int | None,
) -> ScoreEvidenceBatchItemOutput:
    score, reason, is_home, is_disamb, layer = await _score_evidence(
        url=item.url,
        snippet=item.snippet,
        query=query,
        title=item.title,
    )
    if workflow_id is not None:
        await _persist_score(
            workflow_id=workflow_id,
            url=item.url,
            title=item.title,
            snippet=item.snippet,
            score=score,
            reason=reason,
            is_homepage=is_home,
            is_disambiguation=is_disamb,
            score_layer=layer,
        )
    return ScoreEvidenceBatchItemOutput(
        url=item.url,
        score=score,
        reason=reason,
        is_homepage=is_home,
        is_disambiguation=is_disamb,
        score_layer=layer,
    )


class ScoreEvidenceBatchTool(Tool):
    name = "score_evidence_batch"
    description = (
        "批量评估多个 URL 与查询关键词的相关度 (0-10分). "
        "在 search_web 之后一次性调用，把所有搜索结果传进来并行评分. "
        "返回每个 URL 的 score、reason、是否首页、是否歧义命中."
    )
    input_schema = ScoreEvidenceBatchInput
    output_schema = ScoreEvidenceBatchOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, ScoreEvidenceBatchInput)
        log.info(
            "score_evidence_batch_called",
            query=input.query,
            url_count=len(input.items),
        )
        workflow_id = get_workflow_id()

        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SCORES)

        async def _bounded(item: ScoreEvidenceItem) -> ScoreEvidenceBatchItemOutput:
            async with semaphore:
                return await _score_one(input.query, item, workflow_id)

        results = await asyncio.gather(*[_bounded(item) for item in input.items])
        log.info("score_evidence_batch_done", url_count=len(results))
        return ScoreEvidenceBatchOutput(results=results)
