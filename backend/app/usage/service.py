"""Usage service - UPSERT 每日用量记录.

使用 PostgreSQL 的 INSERT ... ON CONFLICT DO UPDATE 实现原子计数器累加.
避免 race condition (并发 workflow 同时跑时, 简单 SELECT+UPDATE 会丢更新).

调用时机:
- POST /workflows 创建 workflow 时: increment_workflow_started
- Celery task 跑完 agent 后: record_workflow_completion (汇总 tool_calls + token)
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, ToolCall, UsageRecord


def _today_utc() -> date:
    """UTC date for period grouping. Workflow 跨时区时统一按 UTC 日期归组."""
    return datetime.now(timezone.utc).date()


def _now_naive_utc() -> datetime:
    """Naive UTC datetime - 跟 model 默认 (datetime.utcnow) 保持一致.

    SQLAlchemy 不会自动把 aware 转 naive, 显式转换避免
    'can't subtract offset-naive and offset-aware datetimes' 错误.
    """
    return datetime.utcnow()


async def increment_workflow_started(
    session: AsyncSession,
    user_id: int,
    *,
    period_date: date | None = None,
) -> UsageRecord:
    """workflow 创建时调用 - workflows_started += 1.

    用 UPSERT 避免并发竞争. 返回更新后的 record.
    """
    target_date = period_date or _today_utc()
    stmt = (
        pg_insert(UsageRecord)
        .values(
            user_id=user_id,
            period_date=target_date,
            workflows_started=1,
        )
        .on_conflict_do_update(
            constraint="uq_user_period",
            set_={
                "workflows_started": UsageRecord.workflows_started + 1,
                "last_updated": _now_naive_utc(),
            },
        )
        .returning(UsageRecord)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    record = result.scalar_one()
    await session.commit()
    return record


async def record_workflow_completion(
    session: AsyncSession,
    user_id: int,
    agent_run: AgentRun,
    tool_calls: list[ToolCall],
    *,
    period_date: date | None = None,
) -> UsageRecord:
    """agent 跑完后汇总 - 把 tool_calls 数 + tokens + 业务资源用量累加进当日记录.

    Args:
        agent_run: 已 finalize 的 AgentRun (status in completed/failed)
        tool_calls: 该 agent_run 的所有 tool_call (用于 token / count 汇总)
    """
    target_date = period_date or _today_utc()

    # 汇总 tool_calls
    n_tool_calls = len(tool_calls)
    n_input_tokens = sum(tc.input_tokens for tc in tool_calls)
    n_output_tokens = sum(tc.output_tokens for tc in tool_calls)
    n_search_queries = sum(1 for tc in tool_calls if tc.tool_name == "search_web")
    n_evidence_fetched = sum(1 for tc in tool_calls if tc.tool_name == "fetch_page")

    # 完成/失败计数
    is_completed = agent_run.status == "completed"
    is_failed = agent_run.status == "failed"

    # UPSERT 累加所有计数器
    stmt = (
        pg_insert(UsageRecord)
        .values(
            user_id=user_id,
            period_date=target_date,
            workflows_completed=1 if is_completed else 0,
            workflows_failed=1 if is_failed else 0,
            tool_calls=n_tool_calls,
            input_tokens=n_input_tokens,
            output_tokens=n_output_tokens,
            search_queries=n_search_queries,
            evidence_fetched=n_evidence_fetched,
        )
        .on_conflict_do_update(
            constraint="uq_user_period",
            set_={
                "workflows_completed": UsageRecord.workflows_completed + (1 if is_completed else 0),
                "workflows_failed": UsageRecord.workflows_failed + (1 if is_failed else 0),
                "tool_calls": UsageRecord.tool_calls + n_tool_calls,
                "input_tokens": UsageRecord.input_tokens + n_input_tokens,
                "output_tokens": UsageRecord.output_tokens + n_output_tokens,
                "search_queries": UsageRecord.search_queries + n_search_queries,
                "evidence_fetched": UsageRecord.evidence_fetched + n_evidence_fetched,
                "last_updated": _now_naive_utc(),
            },
        )
        .returning(UsageRecord)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    record = result.scalar_one()
    await session.commit()
    return record


async def get_user_usage_today(session: AsyncSession, user_id: int) -> UsageRecord | None:
    """查询用户今日用量. 没用过返回 None."""
    stmt = select(UsageRecord).where(
        UsageRecord.user_id == user_id,
        UsageRecord.period_date == _today_utc(),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_usage_range(
    session: AsyncSession,
    user_id: int,
    *,
    start_date: date,
    end_date: date,
) -> dict[str, int]:
    """查询用户某个日期范围内的累计用量 (用于计费/报表).

    返回汇总 dict. 范围内无数据返回全 0.
    """
    stmt = (
        select(
            UsageRecord.workflows_started,
            UsageRecord.workflows_completed,
            UsageRecord.workflows_failed,
            UsageRecord.tool_calls,
            UsageRecord.input_tokens,
            UsageRecord.output_tokens,
            UsageRecord.search_queries,
            UsageRecord.evidence_fetched,
        )
        .where(
            UsageRecord.user_id == user_id,
            UsageRecord.period_date >= start_date,
            UsageRecord.period_date <= end_date,
        )
    )
    rows = (await session.execute(stmt)).all()
    if not rows:
        return {
            "workflows_started": 0,
            "workflows_completed": 0,
            "workflows_failed": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "search_queries": 0,
            "evidence_fetched": 0,
        }
    # 各列求和
    keys = [
        "workflows_started",
        "workflows_completed",
        "workflows_failed",
        "tool_calls",
        "input_tokens",
        "output_tokens",
        "search_queries",
        "evidence_fetched",
    ]
    return {k: sum(getattr(row, k) for row in rows) for k in keys}
