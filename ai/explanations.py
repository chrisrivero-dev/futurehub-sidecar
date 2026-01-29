"""
ai/explanations.py
Pure derivation functions that explain AI decisions using existing data.
NO new classifications, NO new API calls, NO state mutations.
"""

def build_decision_explanation(
    intent_data,
    confidence_score,
    auto_send_decision,
    safety_mode,
    missing_info
):
    # -------------------------------
    # Normalize auto-send decision
    # -------------------------------
    auto_send_allowed = False
    auto_send_reason = "Does not meet safety criteria"

    if isinstance(auto_send_decision, dict):
        if auto_send_decision.get("allowed") is True:
            auto_send_allowed = True
        elif auto_send_decision.get("auto_send") is True:
            auto_send_allowed = True
        elif auto_send_decision.get("eligible") is True:
            auto_send_allowed = True

        if auto_send_decision.get("reason"):
            auto_send_reason = auto_send_decision["reason"]
        elif auto_send_allowed:
            auto_send_reason = "Meets safety criteria"

    else:
        # bool or None
        auto_send_allowed = bool(auto_send_decision)
        if auto_send_allowed:
            auto_send_reason = "Meets safety criteria"

    # -------------------------------
    # Explain auto-send decision
    # -------------------------------
    if auto_send_allowed:
        why_auto_send = f"Auto-send eligible: {auto_send_reason}"
    else:
        why_auto_send = f"Auto-send blocked: {auto_send_reason}"

    # -------------------------------
    # Key signals used
    # -------------------------------
    signals_used = ["intent_classification", "confidence_score"]

    if missing_info:
        signals_used.append("missing_information_detected")

    if intent_data and intent_data.get("secondary_intents"):
        signals_used.append("multiple_intents_detected")

    # -------------------------------
    # Safety explanation
    # -------------------------------
    safety_explanations = {
        "safe": "Response is informational and low-risk",
        "acceptable": "Response is acceptable for auto-send",
        "review_required": "Response requires human review before sending",
        "manual_only": "Issue is too risky for AI assistance",
    }

    safety_explanation = safety_explanations.get(
        safety_mode, "Unknown safety mode"
    )

    # -------------------------------
    # Final payload
    # -------------------------------
    return {
        "why_this_intent": f"Primary intent detected: {intent_data.get('primary_intent')}",
        "why_auto_send_allowed_or_blocked": why_auto_send,
        "confidence_band": (
            "high" if confidence_score >= 0.85
            else "medium" if confidence_score >= 0.65
            else "low"
        ),
        "confidence_description": f"Confidence score: {confidence_score:.2f}",
        "safety_explanation": safety_explanation,
        "missing_information": [] if not missing_info else ["Customer details"],
        "key_signals_used": signals_used,
    }
