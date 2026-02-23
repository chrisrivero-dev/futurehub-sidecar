# models.py
"""
SQLAlchemy models — Postgres Phase 1.
"""

from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Text, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    freshdesk_ticket_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    freshdesk_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def get_or_create_ticket(session, freshdesk_ticket_id: int, freshdesk_domain: str):
    """Fetch existing Ticket by freshdesk_ticket_id or insert a new one."""
    ticket = session.query(Ticket).filter_by(freshdesk_ticket_id=freshdesk_ticket_id).first()
    if not ticket:
        ticket = Ticket(freshdesk_ticket_id=freshdesk_ticket_id, freshdesk_domain=freshdesk_domain)
        session.add(ticket)
        session.flush()
    return ticket


class DraftEvent(Base):
    __tablename__ = "draft_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    safety_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self):
        return (
            f"<DraftEvent id={self.id} intent={self.intent!r} "
            f"mode={self.mode!r} llm_used={self.llm_used}>"
        )


class Reply:
    pass
