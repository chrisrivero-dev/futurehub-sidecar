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


def aggregate_audit_stats(days=7):
    """
    Phase 3 — Audit & governance metrics from JSONL memory.

    Returns:
        {
            "total_tickets": int,
            "automation_rate": float,
            "override_rate": float,
            "followup_rate": float,
            "reopen_rate": float,
            "confidence_distribution": {"high": float, "medium": float, "low": float},
            "risk_distribution": {"low": float, "medium": float, "high": float},
            "top_problematic_intents": [{"intent": str, "followup_rate": float, "override_rate": float}, ...],
        }
    """
    rows = _read_events(days=days)
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

    # --- Automation rate ---
    auto_sent = sum(1 for r in rows if r.get("auto_sent") or r.get("auto_send"))
    automation_rate = round(auto_sent / total, 2)

    # --- Override rate (human_edited / total) ---
    human_edited = sum(1 for r in rows if r.get("human_edited"))
    override_rate = round(human_edited / total, 2)

    # --- Follow-up rate (customer_followup / total) ---
    followup_count = sum(1 for r in rows if r.get("customer_followup"))
    followup_rate = round(followup_count / total, 2)

    # --- Reopen rate ---
    reopen_count = sum(1 for r in rows if r.get("ticket_reopened"))
    reopen_rate = round(reopen_count / total, 2)

    # --- Confidence distribution ---
    conf_counts = {"high": 0, "medium": 0, "low": 0}
    for r in rows:
        bucket = (r.get("confidence_bucket") or "low").lower()
        if bucket in conf_counts:
            conf_counts[bucket] += 1
        else:
            conf_counts["low"] += 1
    confidence_distribution = {
        k: round(v / total, 2) for k, v in conf_counts.items()
    }

    # --- Risk distribution ---
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    for r in rows:
        cat = (r.get("risk_category") or "medium").lower()
        if cat in risk_counts:
            risk_counts[cat] += 1
        else:
            risk_counts["medium"] += 1
    risk_distribution = {
        k: round(v / total, 2) for k, v in risk_counts.items()
    }

    # --- Top problematic intents ---
    # Group by intent, compute per-intent followup_rate and override_rate
    intent_stats = {}
    for r in rows:
        intent = r.get("primary_intent")
        if not intent:
            continue
        if intent not in intent_stats:
            intent_stats[intent] = {"total": 0, "followup": 0, "edited": 0}
        intent_stats[intent]["total"] += 1
        if r.get("customer_followup"):
            intent_stats[intent]["followup"] += 1
        if r.get("human_edited"):
            intent_stats[intent]["edited"] += 1

    problematic = []
    for intent, s in intent_stats.items():
        if s["total"] == 0:
            continue
        fu_rate = round(s["followup"] / s["total"], 2)
        ov_rate = round(s["edited"] / s["total"], 2)
        if fu_rate >= 0.20 or ov_rate >= 0.20:
            problematic.append({
                "intent": intent,
                "count": s["total"],
                "followup_rate": fu_rate,
                "override_rate": ov_rate,
            })

    problematic.sort(
        key=lambda x: x["followup_rate"] + x["override_rate"],
        reverse=True,
    )

    return {
        "total_tickets": total,
        "automation_rate": automation_rate,
        "override_rate": override_rate,
        "followup_rate": followup_rate,
        "reopen_rate": reopen_rate,
        "confidence_distribution": confidence_distribution,
        "risk_distribution": risk_distribution,
        "top_problematic_intents": problematic[:10],
    }
