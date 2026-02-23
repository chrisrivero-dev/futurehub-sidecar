# models.py
<<<<<<< HEAD
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    freshdesk_ticket_id = Column(String, nullable=False)
    freshdesk_domain = Column(String, nullable=False)
    environment = Column(String, nullable=False)

    subject = Column(String)

    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    drafts = relationship("DraftEvent", back_populates="ticket")

    __table_args__ = (
        UniqueConstraint("freshdesk_domain", "freshdesk_ticket_id", name="uix_domain_ticket"),
    )


class DraftEvent(Base):
    __tablename__ = "draft_events"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"))

    intent_label = Column(String)
    confidence_score = Column(Float)
    risk_level = Column(String)
    auto_send_eligible = Column(Boolean)

    draft_text = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="drafts")
=======
"""
SQLAlchemy models — Postgres Phase 1.
"""

from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, UniqueConstraint

from db import Base


class DraftEvent(Base):
    __tablename__ = "draft_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 🔽 ADD THIS
    ticket_id: Mapped[int | None] = mapped_column(
        ForeignKey("tickets.id"),
        nullable=True,
    )

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
        # NEW MODEL — minimal, no extra relationships required

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    freshdesk_ticket_id = Column(String, index=True, nullable=False)
    freshdesk_domain = Column(String, index=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "freshdesk_ticket_id",
            "freshdesk_domain",
            name="uq_ticket_external_id_domain",
        ),
    )

>>>>>>> claude-remove-draft
