# models.py
"""
SQLAlchemy models — Postgres Phase 1.
"""

from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class DraftEvent(Base):
    __tablename__ = "draft_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return (
            f"<DraftEvent id={self.id} intent={self.intent!r} "
            f"mode={self.mode!r} llm_used={self.llm_used}>"
        )


# -------------------------------------------------
# Phase 4A stubs (preserved for backward compat)
# -------------------------------------------------
class Ticket:
    pass


class Reply:
    pass
