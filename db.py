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
    """Create all tables. Safe to call multiple times (IF NOT EXISTS)."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("DB tables ensured (DATABASE_URL=%s)", DATABASE_URL[:30] + "...")
    except Exception as e:
        logger.error("init_db failed (non-fatal): %s", e)


def safe_commit(session):
    """Commit and close. On failure, rollback and log — never raise."""
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("DB commit failed (non-fatal): %s", e)
    finally:
        session.close()
