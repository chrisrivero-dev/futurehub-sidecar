"""
services/memory_service.py
Data access layer for ticket memory.
Writes to data/memory/ticket_events.jsonl (append-only).
Reads via analytics_service.py for aggregation.
"""

import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

JSONL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "memory",
)

JSONL_PATH = os.path.join(JSONL_DIR, "ticket_events.jsonl")


def log_ticket_memory(row: dict) -> None:
    """Append one ticket event as a JSONL line. Called from /api/v1/draft."""
    try:
        os.makedirs(JSONL_DIR, exist_ok=True)
        entry = {
            "created_at": datetime.utcnow().isoformat(),
            "subject": row.get("subject"),
            "latest_message": row.get("latest_message"),
            "primary_intent": row.get("primary_intent"),
            "confidence": row.get("confidence"),
            "safety_mode": row.get("safety_mode"),
            "strategy": row.get("strategy"),
            "auto_send": bool(row.get("auto_send")),
            "auto_send_reason": row.get("auto_send_reason"),
            "draft_outcome": row.get("draft_outcome"),
            "template_id": row.get("template_id"),
            "ambiguity": bool(row.get("ambiguity")),
            "processing_ms": row.get("processing_ms", 0),
        }
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error("Failed to log ticket memory: %s", e)


def _read_events(days=7):
    """Read JSONL rows within the time window. Skips malformed lines."""
    if not os.path.exists(JSONL_PATH):
        return []

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = []

    try:
        with open(JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(row, dict):
                    continue
                if row.get("created_at", "") >= cutoff:
                    rows.append(row)
    except Exception as e:
        logger.error("Failed to read ticket_events.jsonl: %s", e)

    return rows


def get_weekly_ticket_rows(days=7):
    """Return ticket event rows from the last N days."""
    return _read_events(days=days)


def get_recent_intent_count(intent, days=1):
    """Count occurrences of a specific intent in the last N days."""
    rows = _read_events(days=days)
    return sum(1 for r in rows if r.get("primary_intent") == intent)


def get_top_intents(days=7, limit=5):
    """Return top intents by count over the last N days."""
    rows = _read_events(days=days)
    counts = {}
    for r in rows:
        intent = r.get("primary_intent")
        if intent:
            counts[intent] = counts.get(intent, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"intent": k, "count": v} for k, v in ranked[:limit]]


def get_risk_distribution(days=7):
    """Return safety_mode distribution over the last N days."""
    rows = _read_events(days=days)
    dist = {}
    for r in rows:
        mode = r.get("safety_mode") or "unknown"
        dist[mode] = dist.get(mode, 0) + 1
    return dist


def get_automation_stats(days=7):
    """Return auto-send stats over the last N days."""
    rows = _read_events(days=days)
    total = len(rows)
    auto_sent = sum(1 for r in rows if r.get("auto_send"))
    return {"total": total, "auto_sent": auto_sent}
