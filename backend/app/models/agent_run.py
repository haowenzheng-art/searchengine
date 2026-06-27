"""Agent 执行记录 - 一个 Agent run 包含多轮 messages 和多个 tool_calls.

messages 字段存 Anthropic SDK 的完整 messages 历史 (JSONB)，
用于断点续跑：进程崩了，重启后从 messages 恢复继续 tool use 循环。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # FK to workflows.id. 一个 workflow 可以重跑多次 (产生多个 agent_runs).
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    # FK to projects.id. OPC 项目生成的 Agent run.
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # pending / running / completed / failed / interrupted
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # Anthropic messages 历史，断点续跑的关键
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0)
    final_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    workflow: Mapped["Workflow"] = relationship(back_populates="agent_runs")
    project: Mapped["Project | None"] = relationship(back_populates="agent_runs")
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan", order_by="ToolCall.id"
    )

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id} status={self.status} iter={self.current_iteration}>"
