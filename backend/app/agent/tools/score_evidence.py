"""score_evidence tool - 评估 URL 与 query 的相关度.

Phase 2: 三层评估架构 - 规则过滤 + Haiku 粗筛 + Sonnet 复评.
"""
from __future__ import annotations

from pydantic import Field
from sqlalchemy import select

from app.agent.context import get_workflow_id
from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.evidence import Evidence
from app.search.scorer import score_evidence as _score_evidence

log = get_logger(__name__)


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


class ScoreEvidenceInput(ToolInput):
    url: str
    snippet: str
    query: str
    title: str | None = None


class ScoreEvidenceOutput(ToolOutput):
    score: float = Field(ge=0.0, le=10.0)
    reason: str
    is_homepage: bool = False
    is_disambiguation: bool = False
    score_layer: int = 1  # 1=rule, 2=haiku, 3=sonnet


class ScoreEvidenceTool(Tool):
    name = "score_evidence"
    description = (
        "评估单个 URL 与查询关键词的相关度 (0-10分). "
        "决定是否值得抓取正文. score >= 7 进入抓取, <= 3 丢弃, 4-6 由 orchestrator 决定. "
        "返回 score、reason、是否首页、是否歧义命中."
    )
    input_schema = ScoreEvidenceInput
    output_schema = ScoreEvidenceOutput

    async def execute(self, input: ToolInput) -> ToolOutput:
        assert isinstance(input, ScoreEvidenceInput)
        log.info("score_evidence_called", url=input.url, query=input.query)
        score, reason, is_home, is_disamb, layer = await _score_evidence(
            url=input.url,
            snippet=input.snippet,
            query=input.query,
            title=input.title,
        )
        log.info(
            "score_evidence_done",
            url=input.url,
            score=score,
            layer=layer,
            is_homepage=is_home,
            is_disambiguation=is_disamb,
        )

        workflow_id = get_workflow_id()
        if workflow_id is not None:
            await _persist_score(
                workflow_id=workflow_id,
                url=input.url,
                title=input.title,
                snippet=input.snippet,
                score=score,
                reason=reason,
                is_homepage=is_home,
                is_disambiguation=is_disamb,
                score_layer=layer,
            )
        else:
            log.debug("score_evidence_no_workflow_id", url=input.url)

        return ScoreEvidenceOutput(
            score=score,
            reason=reason,
            is_homepage=is_home,
            is_disambiguation=is_disamb,
            score_layer=layer,
        )

