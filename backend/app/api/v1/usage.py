"""Usage API - 当前用户的资源用量.

GET /api/v1/usage/today  今日用量
GET /api/v1/usage/month   本月累计 (用于计费展示)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.db.session import get_db
from app.models import UsageRecord
from app.usage.service import get_user_usage_range, get_user_usage_today

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


class UsageResponse(BaseModel):
    user_id: int
    period_start: date
    period_end: date
    workflows_started: int = 0
    workflows_completed: int = 0
    workflows_failed: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    search_queries: int = 0
    evidence_fetched: int = 0


@router.get("/today", response_model=UsageResponse)
async def get_today_usage(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """今日用量 (UTC date). 没用过返回全 0."""
    today = await get_user_usage_today(db, user.id)
    today_date = date.today()
    if today is None:
        return UsageResponse(
            user_id=user.id,
            period_start=today_date,
            period_end=today_date,
        )
    return UsageResponse(
        user_id=user.id,
        period_start=today.period_date,
        period_end=today.period_date,
        workflows_started=today.workflows_started,
        workflows_completed=today.workflows_completed,
        workflows_failed=today.workflows_failed,
        tool_calls=today.tool_calls,
        input_tokens=today.input_tokens,
        output_tokens=today.output_tokens,
        search_queries=today.search_queries,
        evidence_fetched=today.evidence_fetched,
    )


@router.get("/month", response_model=UsageResponse)
async def get_month_usage(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """本月累计用量 (1 号到今天). 用于计费页展示."""
    today = date.today()
    month_start = today.replace(day=1)
    stats = await get_user_usage_range(
        db, user.id, start_date=month_start, end_date=today
    )
    return UsageResponse(
        user_id=user.id,
        period_start=month_start,
        period_end=today,
        **stats,
    )
