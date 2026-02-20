"""
audit/events.py
Central event emitter with fan-out to SQLite + JSONL stores.
All failures are swallowed — audit must never block draft generation.
"""

import logging
from datetime import datetime

from audit import get_trace_id

logger = logging.getLogger(__name__)

# ── Canonical event types ─────────────────────────────────────
EVENT_TYPES = {
    "ticket_ingested",
    "ai_analyze",
    "draft_generated",
    "delta_validation_result",
    "agent_edited",
    "inserted_into_ticket",
    "tag_applied",
    "customer_reply_received",
    "ticket_reopened",
    "escalated_to_human",
}


def emit_event(event_type, payload=None):
    """
    Emit an audit event to all registered stores.

    Args:
        event_type: One of EVENT_TYPES (validated, but unknown types are still logged).
        payload: dict of event-specific data.

    Returns:
        The trace_id used for the event.
    """
    trace_id = get_trace_id()
    timestamp = datetime.utcnow().isoformat() + "Z"

    if event_type not in EVENT_TYPES:
        logger.warning("Unknown audit event type: %s", event_type)

    event = {
        "trace_id": trace_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "payload": payload or {},
    }

    # Fan-out to all stores — each is independent and non-blocking
    _fan_out(event)

    return trace_id


def _fan_out(event):
    """Write event to SQLite and JSONL. Each store fails independently."""
    # 1) SQLite (structured storage)
    try:
        from audit.store_sqlite import insert_event
        insert_event(event)
    except Exception as e:
        logger.error("audit/store_sqlite write failed: %s", e)

    # 2) JSONL (forensics / append-only)
    try:
        from audit.store_jsonl import append_event
        append_event(event)
    except Exception as e:
        logger.error("audit/store_jsonl write failed: %s", e)
