"""Workflow 模型 - 一次业务流程分析请求.

一个 workflow = 用户提交一个 query (e.g. "招聘筛选流程") → 跑 Agent → 产出报告.
agent_runs / evidence / tool_calls 都通过 workflow_id (int FK) 关联回 workflows.

Phase 3 单租户决策: 不加 tenant_id, 用 user_id 隔离. 未来要多租户时,
给所有业务表加 tenant_id + 中间件即可, 不用重设计.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # owner. 单租户下 user_id 即隔离边界.
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 用户提交的分析主题, e.g. "招聘筛选流程"
    query: Mapped[str] = mapped_column(String(255))
    # 可选上下文, 用户填写行业/规模等补充信息
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # pending / running / completed / failed
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # 失败原因 / 状态说明
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 结构化 MVP 计划, 供 OPC 项目生成使用
    mvp_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关联 (lazy="select" 默认). 业务里用 id 查 agent_runs/evidence 即可, 不强求 join.
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    projects: Mapped[list["Project"]] = relationship(back_populates="workflow")

    def __repr__(self) -> str:
        return f"<Workflow id={self.id} user_id={self.user_id} status={self.status} query={self.query[:40]}>"
