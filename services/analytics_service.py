"""
services/analytics_service.py
Aggregation engine — reads live rows from the draft_events table.
No JSONL. No mocks. No cached summaries.
"""

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _query_draft_events(days=7):
    """Return DraftEvent ORM rows from the last N days. Returns [] on any DB error."""
    try:
        from db import SessionLocal
        from models import DraftEvent

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        session = SessionLocal()
        try:
            return session.query(DraftEvent).filter(DraftEvent.created_at >= cutoff).all()
        finally:
            session.close()
    except Exception as e:
        logger.error("Failed to query draft_events: %s", e)
        return []


def _bucket_confidence(value):
    """Map a confidence float to high/medium/low bucket."""
    if value is None:
        return None
    if value >= 0.80:
        return "high"
    if value >= 0.50:
        return "medium"
    return "low"


def aggregate_weekly_stats(days=7):
    """
    Compute 7-day window stats from live draft_events rows.

    Returns:
        {
            "total_tickets": int,
            "automation_rate": float,
            "followup_rate": float,
            "top_intents": [{"intent": str, "count": int}, ...],
            "risk_distribution": {"low": float, "medium": float, "high": float},
        }
    """
    rows = _query_draft_events(days=days)
    total = len(rows)

    if total == 0:
        return {
            "total_tickets": 0,
            "automation_rate": 0.0,
            "followup_rate": 0.0,
            "top_intents": [],
            "risk_distribution": {"low": 0.0, "medium": 0.0, "high": 0.0},
        }

    # automation_rate: fraction of drafts where LLM was used
    llm_count = sum(1 for r in rows if r.llm_used)
    automation_rate = round(llm_count / total, 2)

    # top_intents from the intent column
    intent_counts = {}
    for r in rows:
        if r.intent:
            intent_counts[r.intent] = intent_counts.get(r.intent, 0) + 1

    top_intents = sorted(
        [{"intent": k, "count": v} for k, v in intent_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # risk_distribution from risk_category column
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for r in rows:
        cat = r.risk_category
        if cat and cat in risk_counts:
            risk_counts[cat] += 1
    risk_total = sum(risk_counts.values())
    risk_distribution = (
        {k: round(v / risk_total, 2) for k, v in risk_counts.items()}
        if risk_total > 0
        else {"low": 0.0, "medium": 0.0, "high": 0.0}
    )

    return {
        "total_tickets": total,
        "automation_rate": automation_rate,
        "followup_rate": 0.0,   # requires post-draft lifecycle events not yet tracked
        "top_intents": top_intents,
        "risk_distribution": risk_distribution,
    }


def aggregate_audit_stats(days=7):
    """
    Audit & governance metrics from live draft_events rows.

    Returns:
        {
            "total_tickets": int,
            "automation_rate": float,
            "override_rate": float,
            "followup_rate": float,
            "reopen_rate": float,
            "confidence_distribution": {"high": float, "medium": float, "low": float},
            "risk_distribution": {"low": float, "medium": float, "high": float},
            "top_problematic_intents": [...],
        }
    """
    rows = _query_draft_events(days=days)
    total = len(rows)

    empty = {
        "total_tickets": 0,
        "automation_rate": 0.0,
        "override_rate": 0.0,
        "followup_rate": 0.0,
        "reopen_rate": 0.0,
        "confidence_distribution": {"high": 0.0, "medium": 0.0, "low": 0.0},
        "risk_distribution": {"low": 0.0, "medium": 0.0, "high": 0.0},
        "top_problematic_intents": [],
    }

    if total == 0:
        return empty

    llm_count = sum(1 for r in rows if r.llm_used)
    automation_rate = round(llm_count / total, 2)

    # confidence_distribution from confidence column
    conf_counts = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        bucket = _bucket_confidence(r.confidence)
        if bucket:
            conf_counts[bucket] += 1
    conf_total = sum(conf_counts.values())
    confidence_distribution = (
        {k: round(v / conf_total, 2) for k, v in conf_counts.items()}
        if conf_total > 0
        else {"high": 0.0, "medium": 0.0, "low": 0.0}
    )

    # risk_distribution from risk_category column
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for r in rows:
        cat = r.risk_category
        if cat and cat in risk_counts:
            risk_counts[cat] += 1
    risk_total = sum(risk_counts.values())
    risk_distribution = (
        {k: round(v / risk_total, 2) for k, v in risk_counts.items()}
        if risk_total > 0
        else {"low": 0.0, "medium": 0.0, "high": 0.0}
    )

    return {
        "total_tickets": total,
        "automation_rate": automation_rate,
        "override_rate": 0.0,   # requires agent-edit lifecycle events not yet tracked
        "followup_rate": 0.0,   # requires customer-reply lifecycle events not yet tracked
        "reopen_rate": 0.0,     # requires ticket-reopen lifecycle events not yet tracked
        "confidence_distribution": confidence_distribution,
        "risk_distribution": risk_distribution,
        "top_problematic_intents": [],  # requires override + followup columns to compute
    }
