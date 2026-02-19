"""
audit/rollup.py
Weekly rollup generator.
Reads from SQLite audit_events + governance_decisions tables
and computes aggregate metrics for a given time window.
"""

import logging
from datetime import datetime, timedelta

from audit.store_sqlite import (
    query_events,
    query_governance_decisions,
    upsert_weekly_rollup,
)

logger = logging.getLogger(__name__)


def compute_weekly_rollup(start_date=None, end_date=None):
    """
    Compute weekly rollup metrics for the given window.

    Args:
        start_date: ISO date string (inclusive). Defaults to 7 days ago.
        end_date:   ISO date string (exclusive). Defaults to now.

    Returns:
        dict with rollup metrics.
    """
    now = datetime.utcnow()
    if not end_date:
        end_date = now.isoformat() + "Z"
    if not start_date:
        start_date = (now - timedelta(days=7)).isoformat() + "Z"

    # ── Gather raw data ───────────────────────────────────────
    events = query_events(since=start_date, limit=100000)
    decisions = query_governance_decisions(since=start_date, limit=100000)

    # ── Event-type counts ─────────────────────────────────────
    type_counts = {}
    for e in events:
        et = e.get("event_type", "unknown")
        type_counts[et] = type_counts.get(et, 0) + 1

    total_tickets = type_counts.get("ticket_ingested", 0)
    total_drafts = type_counts.get("draft_generated", 0)
    total_edits = type_counts.get("agent_edited", 0)
    total_inserts = type_counts.get("inserted_into_ticket", 0)
    total_reopens = type_counts.get("ticket_reopened", 0)
    total_escalations = type_counts.get("escalated_to_human", 0)
    total_replies = type_counts.get("customer_reply_received", 0)

    # ── Governance decision stats ─────────────────────────────
    total_decisions = len(decisions)
    auto_allowed = sum(1 for d in decisions if d.get("auto_send_allowed"))
    auto_blocked = total_decisions - auto_allowed

    # Confidence bucket distribution
    conf_buckets = {"high": 0, "medium": 0, "low": 0}
    for d in decisions:
        bucket = (d.get("confidence_bucket") or "low").lower()
        if bucket in conf_buckets:
            conf_buckets[bucket] += 1
        else:
            conf_buckets["low"] += 1

    # Risk category distribution
    risk_cats = {"low": 0, "medium": 0, "high": 0}
    for d in decisions:
        cat = (d.get("risk_category") or "medium").lower()
        if cat in risk_cats:
            risk_cats[cat] += 1
        else:
            risk_cats["medium"] += 1

    # ── Delta validation stats ────────────────────────────────
    delta_events = [
        e for e in events if e.get("event_type") == "delta_validation_result"
    ]
    delta_total = len(delta_events)
    delta_pass = 0
    delta_fail = 0
    for e in delta_events:
        payload = e.get("payload") or {}
        if isinstance(payload, str):
            import json
            try:
                payload = json.loads(payload)
            except (ValueError, TypeError):
                payload = {}
        if payload.get("validation_passed"):
            delta_pass += 1
        else:
            delta_fail += 1

    # ── Rates (safe division) ─────────────────────────────────
    def _rate(num, denom):
        return round(num / denom, 4) if denom > 0 else 0.0

    metrics = {
        "period": {"start": start_date, "end": end_date},
        "total_tickets_ingested": total_tickets,
        "total_drafts_generated": total_drafts,
        "total_agent_edits": total_edits,
        "total_inserted_into_ticket": total_inserts,
        "total_ticket_reopens": total_reopens,
        "total_escalations": total_escalations,
        "total_customer_replies": total_replies,
        "event_type_counts": type_counts,
        "governance": {
            "total_decisions": total_decisions,
            "auto_send_allowed": auto_allowed,
            "auto_send_blocked": auto_blocked,
            "auto_send_rate": _rate(auto_allowed, total_decisions),
        },
        "confidence_distribution": {
            k: _rate(v, total_decisions) for k, v in conf_buckets.items()
        },
        "risk_distribution": {
            k: _rate(v, total_decisions) for k, v in risk_cats.items()
        },
        "delta_validation": {
            "total": delta_total,
            "passed": delta_pass,
            "failed": delta_fail,
            "pass_rate": _rate(delta_pass, delta_total),
        },
        "edit_rate": _rate(total_edits, total_drafts),
        "escalation_rate": _rate(total_escalations, total_tickets),
        "reopen_rate": _rate(total_reopens, total_tickets),
    }

    # ── Persist to SQLite ─────────────────────────────────────
    try:
        upsert_weekly_rollup(
            week_start=start_date,
            week_end=end_date,
            generated_at=datetime.utcnow().isoformat() + "Z",
            metrics=metrics,
        )
    except Exception as e:
        logger.error("Failed to persist weekly rollup: %s", e)

    return metrics
