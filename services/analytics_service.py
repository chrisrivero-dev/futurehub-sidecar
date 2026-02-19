"""
services/analytics_service.py
Phase 2 — JSONL-based aggregation engine.
Reads from data/memory/ticket_events.jsonl.
Pure math. No LLM. No database. No background workers.
"""

import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

JSONL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "memory",
    "ticket_events.jsonl",
)


def _read_events(days=7):
    """
    Read ticket_events.jsonl and return rows within the time window.
    Handles: missing file, empty file, malformed rows.
    """
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
                    continue  # skip malformed rows

                if not isinstance(row, dict):
                    continue

                ts = row.get("created_at", "")
                if ts >= cutoff:
                    rows.append(row)
    except Exception as e:
        logger.error("Failed to read ticket_events.jsonl: %s", e)

    return rows


def aggregate_weekly_stats(days=7):
    """
    Compute 7-day window stats from JSONL memory.

    Returns:
        {
            "total_tickets": int,
            "automation_rate": float,
            "followup_rate": float,
            "top_intents": [{"intent": str, "count": int}, ...],
            "risk_distribution": {"low": float, "medium": float, "high": float},
        }
    """
    rows = _read_events(days=days)
    total = len(rows)

    if total == 0:
        return {
            "total_tickets": 0,
            "automation_rate": 0.0,
            "followup_rate": 0.0,
            "top_intents": [],
            "risk_distribution": {"low": 0.0, "medium": 0.0, "high": 0.0},
        }

    # --- Automation rate ---
    auto_sent = sum(1 for r in rows if r.get("auto_send"))
    automation_rate = round(auto_sent / total, 2)

    # --- Follow-up rate (draft_only or non-auto-send = followup) ---
    followup_outcomes = {
        "follow-up expected",
        "followup_expected",
        "follow_up_expected",
        "draft_only",
    }
    followup_count = sum(
        1 for r in rows
        if (r.get("draft_outcome") or "").lower() in followup_outcomes
    )
    followup_rate = round(followup_count / total, 2)

    # --- Top intents (top 5) ---
    intent_counts = {}
    for r in rows:
        intent = r.get("primary_intent")
        if intent:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    top_intents = sorted(
        [{"intent": k, "count": v} for k, v in intent_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # --- Risk distribution ---
    risk_map = {"safe": "low", "review_required": "medium", "unsafe": "high"}
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for r in rows:
        safety = (r.get("safety_mode") or "").lower()
        level = risk_map.get(safety, "medium")
        risk_counts[level] += 1

    risk_distribution = {
        k: round(v / total, 2) for k, v in risk_counts.items()
    }

    return {
        "total_tickets": total,
        "automation_rate": automation_rate,
        "followup_rate": followup_rate,
        "top_intents": top_intents,
        "risk_distribution": risk_distribution,
    }
