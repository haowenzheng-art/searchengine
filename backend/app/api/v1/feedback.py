"""证据反馈 API - 报告页 👍/👎 按钮调用.

POST /api/v1/evidence/{evidence_id}/feedback
  body: {useful: bool, comment?: str, user_id: str}
  返回: {feedback_id, useful}

GET /api/v1/evidence/{evidence_id}/feedback
  查询某条证据的反馈统计 (供 UI 显示)
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Evidence, EvidenceFeedback

router = APIRouter(prefix="/api/v1/evidence", tags=["feedback"])


class FeedbackRequest(BaseModel):
    useful: bool
    comment: str | None = None
    # Phase 3 才有真实 auth, 现在用 client 传的 user_id
    user_id: str = Field(min_length=1, max_length=64)


class FeedbackResponse(BaseModel):
    feedback_id: int
    evidence_id: int
    useful: bool
    created_at: datetime


class FeedbackStats(BaseModel):
    evidence_id: int
    useful_count: int
    not_useful_count: int
    total: int


@router.post("/{evidence_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    evidence_id: int,
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """提交用户对某条证据的反馈.

    每个用户对每条证据只能反馈一次, 重复提交更新已有记录.
    """
    # 验证 evidence 存在
    evidence = await db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="evidence not found")

    # 查是否已有反馈
    stmt = select(EvidenceFeedback).where(
        EvidenceFeedback.evidence_id == evidence_id,
        EvidenceFeedback.user_id == request.user_id,
    )
    existing = (await db.execute(stmt)).scalars().first()

    if existing:
        # 更新已有反馈
        existing.useful = request.useful
        existing.comment = request.comment
        await db.commit()
        await db.refresh(existing)
        feedback = existing
    else:
        # 新建反馈
        feedback = EvidenceFeedback(
            evidence_id=evidence_id,
            user_id=request.user_id,
            useful=request.useful,
            comment=request.comment,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

    return FeedbackResponse(
        feedback_id=feedback.id,
        evidence_id=feedback.evidence_id,
        useful=feedback.useful,
        created_at=feedback.created_at,
    )


@router.get("/{evidence_id}/feedback", response_model=FeedbackStats)
async def get_feedback_stats(
    evidence_id: int,
    db: AsyncSession = Depends(get_db),
):
    """查询某条证据的反馈统计."""
    evidence = await db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="evidence not found")

    stmt = (
        select(
            EvidenceFeedback.useful,
            func.count(EvidenceFeedback.id),
        )
        .where(EvidenceFeedback.evidence_id == evidence_id)
        .group_by(EvidenceFeedback.useful)
    )
    rows = (await db.execute(stmt)).all()

    useful_count = sum(count for useful, count in rows if useful)
    not_useful_count = sum(count for useful, count in rows if not useful)

    return FeedbackStats(
        evidence_id=evidence_id,
        useful_count=useful_count,
        not_useful_count=not_useful_count,
        total=useful_count + not_useful_count,
    )
