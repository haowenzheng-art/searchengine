"""Usage 记录 - 每用户每天一行, 汇总当天资源用量.

Phase 3 决策: Stripe 延后, 但先做用量统计. 这表是计费基础 -
未来 Stripe 计费时按 period_date 范围 sum 即可.

设计选择 (列 vs 行):
- 列式 (counters 在一行): 查询快, 加字段不需要改 schema 多.
- 行式 (resource_type + count): 灵活但要 GROUP BY. Phase 3 用量统计字段有限, 列式更简单.

更新策略: UPSERT (ON CONFLICT DO UPDATE SET counter = counter + X).
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        # 一个用户一天只能有一行
        UniqueConstraint("user_id", "period_date", name="uq_user_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    period_date: Mapped[date] = mapped_column(Date, index=True)

    # 计数器 (UPSERT 累加)
    workflows_started: Mapped[int] = mapped_column(Integer, default=0)
    workflows_completed: Mapped[int] = mapped_column(Integer, default=0)
    workflows_failed: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    # orchestrator LLM 调用累计 token (tool 内部 LLM tokens 已在 tool_calls 表, 不重复记)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # 业务级资源用量
    search_queries: Mapped[int] = mapped_column(Integer, default=0)
    evidence_fetched: Mapped[int] = mapped_column(Integer, default=0)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<UsageRecord user_id={self.user_id} date={self.period_date} workflows={self.workflows_started}>"
