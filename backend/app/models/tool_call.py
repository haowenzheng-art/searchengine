"""单个 tool 调用记录 - 每次 LLM 调用 tool 都持久化.

用于：调试、审计、计费（按 token）、性能分析。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(64))
    # Anthropic SDK 的 tool_use id (用于 tool_result 关联)
    tool_call_id: Mapped[str] = mapped_column(String(128))
    iteration: Mapped[int] = mapped_column(Integer, default=0)

    input_args: Mapped[dict[str, Any]] = mapped_column(JSONB)
    output_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent_run: Mapped["AgentRun"] = relationship(back_populates="tool_calls")

    def __repr__(self) -> str:
        return f"<ToolCall id={self.id} tool={self.tool_name} iter={self.iteration}>"
