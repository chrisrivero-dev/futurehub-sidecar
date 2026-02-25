# db.py
"""
Database engine and session management.
Uses DATABASE_URL env var. Falls back to SQLite for local dev.
All writes are wrapped in safe try/except — DB being down must never
break the draft pipeline.
"""

import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///data/sidecar.db",
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    # Import models so SQLAlchemy registers tables
    import models  # IMPORTANT — ensures table metadata is loaded
    Base.metadata.create_all(bind=engine)


def safe_commit(session):
    """Commit and close. On failure, rollback and log — never raise."""
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("DB commit failed (non-fatal): %s", e)
    finally:
        session.close()

def get_or_create_ticket(session, freshdesk_ticket_id: str, freshdesk_domain: str):
    """
    Non-blocking helper: returns Ticket or None.
    Never raises.
    """
    try:
        # Import locally to avoid circular import
        from models import Ticket

        ticket = (
            session.query(Ticket)
            .filter_by(
                freshdesk_ticket_id=freshdesk_ticket_id,
                freshdesk_domain=freshdesk_domain,
            )
            .first()
        )

        if ticket:
            return ticket

        ticket = Ticket(
            freshdesk_ticket_id=freshdesk_ticket_id,
            freshdesk_domain=freshdesk_domain,
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        return ticket

    except Exception:
        session.rollback()
        return None
