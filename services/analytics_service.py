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

    try:
        from db import SessionLocal
        from models import DraftEvent, TicketReply, TicketStatusChange

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        session = SessionLocal()
        try:
            rows = session.query(DraftEvent).filter(DraftEvent.created_at >= cutoff).all()
            total = len(rows)

            if total == 0:
                return empty

            # automation_rate
            llm_count = sum(1 for r in rows if r.llm_used)
            automation_rate = round(llm_count / total, 2)

            # confidence_distribution
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

            # risk_distribution
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

            # override_rate: outbound replies where edited=True / total outbound replies
            outbound_replies = (
                session.query(TicketReply)
                .filter(
                    TicketReply.direction == "outbound",
                    TicketReply.created_at >= cutoff,
                )
                .all()
            )
            total_outbound = len(outbound_replies)
            edited_count = sum(1 for r in outbound_replies if r.edited is True)
            override_rate = round(edited_count / total_outbound, 2) if total_outbound > 0 else 0.0

            # followup_rate: DraftEvents in window that have >= 1 inbound TicketReply
            # created after the draft's created_at, using ticket_id linkage
            draft_ticket_ids = {r.ticket_id: r.created_at for r in rows if r.ticket_id is not None}
            followup_count = 0
            if draft_ticket_ids:
                inbound_replies = (
                    session.query(TicketReply)
                    .filter(
                        TicketReply.direction == "inbound",
                        TicketReply.ticket_id.in_(list(draft_ticket_ids.keys())),
                        TicketReply.created_at >= cutoff,
                    )
                    .all()
                )
                tickets_with_followup = {
                    r.ticket_id
                    for r in inbound_replies
                    if r.created_at > draft_ticket_ids.get(r.ticket_id, r.created_at)
                }
                followup_count = len(tickets_with_followup)
            followup_rate = round(followup_count / total, 2)

            # reopen_rate: status changes where old in (resolved/closed) and new == open
            status_changes = (
                session.query(TicketStatusChange)
                .filter(TicketStatusChange.created_at >= cutoff)
                .all()
            )
            total_changes = len(status_changes)
            reopen_count = sum(
                1 for s in status_changes
                if s.old_status in ("resolved", "closed") and s.new_status == "open"
            )
            reopen_rate = round(reopen_count / total_changes, 2) if total_changes > 0 else 0.0

        finally:
            session.close()

    except Exception:
        return empty

    return {
        "total_tickets": total,
        "automation_rate": automation_rate,
        "override_rate": override_rate,
        "followup_rate": followup_rate,
        "reopen_rate": reopen_rate,
        "confidence_distribution": confidence_distribution,
        "risk_distribution": risk_distribution,
        "top_problematic_intents": [],
    }
