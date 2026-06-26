"""score_evidence tool - 评估 URL 与 query 的相关度.

Phase 1: stub 实现，所有 URL 都返回 score=8.0 (通过阈值).
Phase 2: 三层评估架构 - 规则过滤 + Haiku 粗筛 + Sonnet 复评.
"""
from __future__ import annotations

from pydantic import Field

from app.agent.tools.base import Tool, ToolInput, ToolOutput
from app.core.logging import get_logger

log = get_logger(__name__)


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
        # Phase 1 stub: 直接给 8.0 让 orchestrator 能跑通
        # Phase 2 替换为三层评估: 规则 -> Haiku -> Sonnet
        return ScoreEvidenceOutput(
            score=8.0,
            reason="Phase 1 stub - all URLs pass. Phase 2 will use three-layer scoring.",
            is_homepage=False,
            is_disambiguation=False,
            score_layer=1,
        )
