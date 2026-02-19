"""
audit/store_sqlite.py
SQLite-backed structured audit storage.
Tables: audit_events, governance_decisions, weekly_rollups.
All DDL uses CREATE TABLE IF NOT EXISTS — safe for cold starts.
"""

import json
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "audit.db",
)


def _get_conn():
    """Return a new SQLite connection with WAL mode for concurrent reads."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn):
    """Create tables if they don't exist. Idempotent."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id    TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            payload     TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_ae_trace
            ON audit_events(trace_id);
        CREATE INDEX IF NOT EXISTS idx_ae_type_ts
            ON audit_events(event_type, timestamp);

        CREATE TABLE IF NOT EXISTS governance_decisions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id            TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            intent              TEXT,
            confidence          REAL,
            risk_level          TEXT,
            sensitive_flag      INTEGER DEFAULT 0,
            auto_send_allowed   INTEGER DEFAULT 0,
            reason              TEXT,
            confidence_bucket   TEXT,
            risk_category       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_gd_trace
            ON governance_decisions(trace_id);

        CREATE TABLE IF NOT EXISTS weekly_rollups (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start      TEXT NOT NULL,
            week_end        TEXT NOT NULL,
            generated_at    TEXT NOT NULL,
            metrics         TEXT NOT NULL DEFAULT '{}'
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_wr_week
            ON weekly_rollups(week_start, week_end);
    """)


_TABLES_ENSURED = False


def _conn_with_tables():
    """Return a connection with tables guaranteed to exist."""
    global _TABLES_ENSURED
    conn = _get_conn()
    if not _TABLES_ENSURED:
        _ensure_tables(conn)
        _TABLES_ENSURED = True
    return conn


# ── Public API ────────────────────────────────────────────────

def insert_event(event):
    """Insert a single audit event row."""
    conn = _conn_with_tables()
    try:
        conn.execute(
            "INSERT INTO audit_events (trace_id, event_type, timestamp, payload) "
            "VALUES (?, ?, ?, ?)",
            (
                event["trace_id"],
                event["event_type"],
                event["timestamp"],
                json.dumps(event.get("payload", {})),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def insert_governance_decision(decision):
    """Insert a governance decision row."""
    conn = _conn_with_tables()
    try:
        conn.execute(
            "INSERT INTO governance_decisions "
            "(trace_id, timestamp, intent, confidence, risk_level, "
            " sensitive_flag, auto_send_allowed, reason, confidence_bucket, risk_category) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision["trace_id"],
                decision["timestamp"],
                decision.get("intent"),
                decision.get("confidence"),
                decision.get("risk_level"),
                int(decision.get("sensitive_flag", False)),
                int(decision.get("auto_send_allowed", False)),
                decision.get("reason"),
                decision.get("confidence_bucket"),
                decision.get("risk_category"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_weekly_rollup(week_start, week_end, generated_at, metrics):
    """Insert or replace a weekly rollup row."""
    conn = _conn_with_tables()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO weekly_rollups "
            "(week_start, week_end, generated_at, metrics) "
            "VALUES (?, ?, ?, ?)",
            (week_start, week_end, generated_at, json.dumps(metrics)),
        )
        conn.commit()
    finally:
        conn.close()


def query_events(event_type=None, since=None, limit=500):
    """
    Query audit events with optional filters.
    Returns list of dicts.
    """
    conn = _conn_with_tables()
    try:
        clauses = []
        params = []
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM audit_events{where} ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_governance_decisions(since=None, limit=500):
    """Query governance decisions with optional time filter."""
    conn = _conn_with_tables()
    try:
        if since:
            rows = conn.execute(
                "SELECT * FROM governance_decisions WHERE timestamp >= ? "
                "ORDER BY id DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM governance_decisions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_latest_rollup():
    """Return the most recent weekly rollup or None."""
    conn = _conn_with_tables()
    try:
        row = conn.execute(
            "SELECT * FROM weekly_rollups ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            result = dict(row)
            result["metrics"] = json.loads(result["metrics"])
            return result
        return None
    finally:
        conn.close()
