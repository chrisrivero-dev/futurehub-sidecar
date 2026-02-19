"""
services/memory_service.py
Data access layer for ticket_memory table.
Raw sqlite3, parameterized queries, no ORM.
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "ticket_memory.db",
)


def _get_connection():
    """Open a sqlite3 connection, creating DB + table if needed."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticket_memory (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            subject         TEXT,
            latest_message  TEXT,
            primary_intent  TEXT,
            confidence      REAL,
            safety_mode     TEXT,
            strategy        TEXT,
            auto_send       INTEGER DEFAULT 0,
            auto_send_reason TEXT,
            draft_outcome   TEXT,
            template_id     TEXT,
            ambiguity       INTEGER DEFAULT 0,
            processing_ms   INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def log_ticket_memory(row: dict) -> None:
    """Insert one ticket record into memory. Called from /api/v1/draft."""
    try:
        conn = _get_connection()
        conn.execute(
            """
            INSERT INTO ticket_memory
                (subject, latest_message, primary_intent, confidence,
                 safety_mode, strategy, auto_send, auto_send_reason,
                 draft_outcome, template_id, ambiguity, processing_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("subject"),
                row.get("latest_message"),
                row.get("primary_intent"),
                row.get("confidence"),
                row.get("safety_mode"),
                row.get("strategy"),
                1 if row.get("auto_send") else 0,
                row.get("auto_send_reason"),
                row.get("draft_outcome"),
                row.get("template_id"),
                1 if row.get("ambiguity") else 0,
                row.get("processing_ms", 0),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to log ticket memory: %s", e)


def get_weekly_ticket_rows(days=7):
    """Return all ticket_memory rows from the last N days."""
    try:
        conn = _get_connection()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT * FROM ticket_memory WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error("get_weekly_ticket_rows error: %s", e)
        return []


def get_recent_intent_count(intent, days=1):
    """Count occurrences of a specific intent in the last N days."""
    try:
        conn = _get_connection()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM ticket_memory WHERE primary_intent = ? AND created_at >= ?",
            (intent, cutoff),
        ).fetchone()
        conn.close()
        return row["cnt"] if row else 0
    except Exception as e:
        logger.error("get_recent_intent_count error: %s", e)
        return 0


def get_top_intents(days=7, limit=5):
    """Return top intents by count over the last N days."""
    try:
        conn = _get_connection()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """
            SELECT primary_intent, COUNT(*) as count
            FROM ticket_memory
            WHERE created_at >= ? AND primary_intent IS NOT NULL
            GROUP BY primary_intent
            ORDER BY count DESC
            LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()
        conn.close()
        return [{"intent": r["primary_intent"], "count": r["count"]} for r in rows]
    except Exception as e:
        logger.error("get_top_intents error: %s", e)
        return []


def get_risk_distribution(days=7):
    """Return safety_mode distribution over the last N days."""
    try:
        conn = _get_connection()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """
            SELECT safety_mode, COUNT(*) as count
            FROM ticket_memory
            WHERE created_at >= ?
            GROUP BY safety_mode
            """,
            (cutoff,),
        ).fetchall()
        conn.close()
        return {r["safety_mode"] or "unknown": r["count"] for r in rows}
    except Exception as e:
        logger.error("get_risk_distribution error: %s", e)
        return {}


def get_automation_stats(days=7):
    """Return auto-send stats over the last N days."""
    try:
        conn = _get_connection()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        row = conn.execute(
            """
            SELECT
                COUNT(*)                          as total,
                SUM(CASE WHEN auto_send = 1 THEN 1 ELSE 0 END) as auto_sent
            FROM ticket_memory
            WHERE created_at >= ?
            """,
            (cutoff,),
        ).fetchone()
        conn.close()
        total = row["total"] if row else 0
        auto_sent = row["auto_sent"] if row else 0
        return {"total": total, "auto_sent": auto_sent}
    except Exception as e:
        logger.error("get_automation_stats error: %s", e)
        return {"total": 0, "auto_sent": 0}
