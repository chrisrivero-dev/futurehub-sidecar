# models.py
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
