"""
governance/evaluator.py
Unified governance evaluator — advisory-only by default.
Replaces ad-hoc should_auto_send() with a richer evaluation
that emits audit events and logs governance decisions.
"""

import logging
from datetime import datetime

from audit import get_trace_id
from audit.events import emit_event
from audit.store_sqlite import insert_governance_decision

logger = logging.getLogger(__name__)

# ── Configurable thresholds ───────────────────────────────────
AUTO_SEND_CONFIDENCE_THRESHOLD = 0.80
SAFE_RISK_LEVELS = {"low"}
ALLOWED_INTENTS = {
    "shipping_status",
    "firmware_update",
    "firmware_update_info",
    "factory_reset",
}


def evaluate_send_readiness(
    intent,
    confidence,
    risk_level,
    safety_mode,
    sensitive_flag=False,
    ambiguity_detected=False,
    has_required_missing=False,
    delta_passed=True,
):
    """
    Evaluate whether a draft is ready for auto-send.

    Advisory-only: returns a decision dict but does NOT send.
    Emits audit events and persists governance decision.

    Args:
        intent: Normalized intent string.
        confidence: Float 0..1.
        risk_level: "low" / "medium" / "high".
        safety_mode: Raw safety mode from classifier.
        sensitive_flag: Whether sensitive content was detected.
        ambiguity_detected: Whether intent classification was ambiguous.
        has_required_missing: Whether required variables are missing.
        delta_passed: Whether delta validation passed.

    Returns:
        {
            "auto_send_allowed": bool,
            "reasons": [str, ...],
            "risk_category": str,
            "confidence_bucket": str,
            "trace_id": str,
        }
    """
    trace_id = get_trace_id()
    reasons = []
    allowed = True

    # ── Gate 1: Sensitive content ─────────────────────────────
    if sensitive_flag:
        allowed = False
        reasons.append("Blocked: sensitive content detected")

    # ── Gate 2: Risk level ────────────────────────────────────
    if (risk_level or "").lower() not in SAFE_RISK_LEVELS:
        allowed = False
        reasons.append(f"Blocked: risk_level='{risk_level}' (must be 'low')")

    # ── Gate 3: Confidence threshold ──────────────────────────
    if confidence < AUTO_SEND_CONFIDENCE_THRESHOLD:
        allowed = False
        reasons.append(
            f"Blocked: confidence {confidence:.2f} < "
            f"{AUTO_SEND_CONFIDENCE_THRESHOLD:.2f}"
        )

    # ── Gate 4: Intent allowlist ──────────────────────────────
    if intent not in ALLOWED_INTENTS:
        allowed = False
        reasons.append(f"Blocked: intent '{intent}' not in auto-send allowlist")

    # ── Gate 5: Ambiguity ─────────────────────────────────────
    if ambiguity_detected:
        allowed = False
        reasons.append("Blocked: ambiguity detected in classification")

    # ── Gate 6: Required variables ────────────────────────────
    if has_required_missing:
        allowed = False
        reasons.append("Blocked: required variables are missing")

    # ── Gate 7: Delta validation ──────────────────────────────
    if not delta_passed:
        allowed = False
        reasons.append("Blocked: delta validation failed")

    if not reasons:
        reasons.append(
            f"Allowed: intent='{intent}', confidence={confidence:.2f}, "
            f"risk='{risk_level}'"
        )

    # ── Compute buckets ───────────────────────────────────────
    confidence_bucket = _confidence_bucket(confidence)
    risk_category = _risk_category(safety_mode)

    # ── Persist governance decision (non-blocking) ────────────
    try:
        insert_governance_decision({
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "intent": intent,
            "confidence": confidence,
            "risk_level": risk_level,
            "sensitive_flag": sensitive_flag,
            "auto_send_allowed": allowed,
            "reason": "; ".join(reasons),
            "confidence_bucket": confidence_bucket,
            "risk_category": risk_category,
        })
    except Exception as e:
        logger.error("Failed to persist governance decision: %s", e)

    return {
        "auto_send_allowed": allowed,
        "reasons": reasons,
        "risk_category": risk_category,
        "confidence_bucket": confidence_bucket,
        "trace_id": trace_id,
    }


def _confidence_bucket(confidence):
    """Map confidence float to bucket label."""
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.50:
        return "medium"
    return "low"


def _risk_category(safety_mode):
    """Map safety_mode to risk category."""
    mapping = {"safe": "low", "review_required": "medium", "unsafe": "high"}
    return mapping.get((safety_mode or "").lower(), "medium")
