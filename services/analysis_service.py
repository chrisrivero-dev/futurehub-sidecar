"""
services/analysis_service.py
Pure math + aggregation. No LLM calls, no AI prompts.
Input: rows from memory_service
Output: structured analytics JSON
"""


def aggregate_weekly_stats(rows):
    """
    Compute weekly analytics from ticket_memory rows.

    Returns:
        {
            "total_tickets": int,
            "automation_rate": float,
            "followup_rate": float,
            "top_intents": [{"intent": str, "count": int}, ...],
            "risk_distribution": {"low": float, "medium": float, "high": float},
        }
    """
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

    # --- Follow-up rate ---
    followup_count = sum(
        1 for r in rows
        if (r.get("draft_outcome") or "").lower() in (
            "follow-up expected",
            "followup_expected",
            "follow_up_expected",
        )
    )
    followup_rate = round(followup_count / total, 2)

    # --- Top intents ---
    intent_counts = {}
    for r in rows:
        intent = r.get("primary_intent")
        if intent:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    top_intents = sorted(
        [{"intent": k, "count": v} for k, v in intent_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    # --- Risk distribution ---
    # Map safety_mode to risk level
    risk_map = {
        "safe": "low",
        "review_required": "medium",
        "unsafe": "high",
    }
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
