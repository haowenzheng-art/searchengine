"""用户证据反馈 - 报告页 👍/👎 按钮.

每个用户对每条证据只能反馈一次 (UNIQUE 约束).
反馈不影响当前报告, 进入离线分析扩充黄金集 (Phase 5+).
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvidenceFeedback(Base):
    __tablename__ = "evidence_feedback"
    __table_args__ = (
        # 每个用户对每条证据只能反馈一次
        UniqueConstraint("evidence_id", "user_id", name="uq_evidence_user_feedback"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    # Phase 3 才有 users 表, 先用 string 占位
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    useful: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EvidenceFeedback id={self.id} evidence={self.evidence_id} useful={self.useful}>"
