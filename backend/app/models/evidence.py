"""证据链记录 - 每个 URL 一条.

Phase 2 实现 scorer 填 score/score_reason/is_homepage/is_disambiguation。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # FK to workflows.id. 一个 workflow 可能有多条证据.
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    # Phase 2 scorer 填的字段
    score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    score_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_homepage: Mapped[bool] = mapped_column(Boolean, default=False)
    is_disambiguation: Mapped[bool] = mapped_column(Boolean, default=False)
    score_layer: Mapped[int] = mapped_column(Integer, default=0)  # 1=rule, 2=haiku, 3=sonnet

    fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} score={self.score} url={self.url[:60]}>"
