"""
audit/store_jsonl.py
Append-only JSONL audit log for forensics.
Separate from ticket_events.jsonl — this is the raw audit trail.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

AUDIT_JSONL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "audit",
)

AUDIT_JSONL_PATH = os.path.join(AUDIT_JSONL_DIR, "audit_events.jsonl")


def append_event(event):
    """Append one audit event as a JSONL line."""
    try:
        os.makedirs(AUDIT_JSONL_DIR, exist_ok=True)
        line = json.dumps({
            "trace_id": event["trace_id"],
            "event_type": event["event_type"],
            "timestamp": event["timestamp"],
            "payload": event.get("payload", {}),
        })
        with open(AUDIT_JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        logger.error("Failed to append audit JSONL: %s", e)


def read_events(since=None, event_type=None, limit=500):
    """
    Read audit events from the JSONL file with optional filters.
    Returns list of dicts, most recent first.
    """
    if not os.path.exists(AUDIT_JSONL_PATH):
        return []

    rows = []
    try:
        with open(AUDIT_JSONL_PATH, "r", encoding="utf-8") as f:
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
                if since and row.get("timestamp", "") < since:
                    continue
                if event_type and row.get("event_type") != event_type:
                    continue
                rows.append(row)
    except Exception as e:
        logger.error("Failed to read audit JSONL: %s", e)

    rows.reverse()
    return rows[:limit]
