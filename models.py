# models.py
"""
SQLAlchemy models — Postgres Phase 1.
"""

from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Text, Integer, BigInteger, ForeignKey, Float
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
    draft_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


class TicketReply(Base):
    """Outbound agent replies and inbound customer replies received via Freshdesk webhook."""
    __tablename__ = "ticket_replies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    draft_event_id: Mapped[int | None] = mapped_column(ForeignKey("draft_events.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # 'outbound' | 'inbound'
    freshdesk_conversation_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    body_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edited: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class TicketStatusChange(Base):
    """Ticket status transitions received via Freshdesk webhook."""
    __tablename__ = "ticket_status_changes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    old_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    freshdesk_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class Reply:
    pass
