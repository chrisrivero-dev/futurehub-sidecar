"""
services/governance_service.py
Phase 3 — Audit & Automation Governance Layer.
Gating decision logic for auto-send.
Does NOT modify classifier, intent, or draft logic.
"""

# Configurable threshold (can be overridden via env in future)
AUTO_SEND_CONFIDENCE_THRESHOLD = 0.80


def should_auto_send(intent, confidence, risk_level, sensitive_flag):
    """
    Determine whether auto-send is allowed for this ticket.

    Rules (ALL must be true):
      - risk_level == "low"
      - confidence >= AUTO_SEND_CONFIDENCE_THRESHOLD
      - sensitive_flag == False

    Returns:
        {"auto_send_allowed": bool, "reason": str}
    """
    if sensitive_flag:
        return {
            "auto_send_allowed": False,
            "reason": "Blocked: sensitive content detected",
        }

    if (risk_level or "").lower() != "low":
        return {
            "auto_send_allowed": False,
            "reason": f"Blocked: risk_level='{risk_level}' (must be 'low')",
        }

    if confidence < AUTO_SEND_CONFIDENCE_THRESHOLD:
        return {
            "auto_send_allowed": False,
            "reason": (
                f"Blocked: confidence {confidence:.2f} < "
                f"{AUTO_SEND_CONFIDENCE_THRESHOLD:.2f}"
            ),
        }

    return {
        "auto_send_allowed": True,
        "reason": (
            f"Allowed: intent='{intent}', confidence={confidence:.2f}, "
            f"risk='{risk_level}'"
        ),
    }


def compute_confidence_bucket(confidence):
    """Map a confidence float to a bucket label."""
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.50:
        return "medium"
    return "low"


def compute_risk_category(safety_mode):
    """Map safety_mode to a risk category."""
    mapping = {"safe": "low", "review_required": "medium", "unsafe": "high"}
    return mapping.get((safety_mode or "").lower(), "medium")
