"""
SQLAlchemy models — Postgres Phase 1.
"""

from datetime import datetime, timezone


from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Column,
    Integer,
    UniqueConstraint,
    BigInteger,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class DraftEvent(Base):
    __tablename__ = "draft_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"),
        nullable=True,
    )

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    draft_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return (
            f"<DraftEvent id={self.id} intent={self.intent!r} "
            f"mode={self.mode!r} llm_used={self.llm_used}>"
        )


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    freshdesk_ticket_id = Column(String, index=True, nullable=False)
    freshdesk_domain = Column(String, index=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "freshdesk_ticket_id",
            "freshdesk_domain",
            name="uq_ticket_external_id_domain",
        ),
    )
    from sqlalchemy import BigInteger, Index


class TicketReply(Base):
    __tablename__ = "ticket_replies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    draft_event_id = Column(Integer, ForeignKey("draft_events.id"), nullable=True)

    direction = Column(String(10), nullable=False)  # 'outbound' or 'inbound'
    freshdesk_conversation_id = Column(BigInteger, nullable=False, unique=True)

    body_hash = Column(String(64), nullable=True)
    body_length = Column(Integer, nullable=True)

    edited = Column(Boolean, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_tr_ticket", "ticket_id"),
        Index("ix_tr_dir_created", "direction", "created_at"),
    )


class TicketStatusChange(Base):
    __tablename__ = "ticket_status_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    old_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)

    freshdesk_updated_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_tsc_ticket", "ticket_id"),
        Index("ix_tsc_new_created", "new_status", "created_at"),
    )