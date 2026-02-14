"""
Auto-Send Classifier
HARD deny-by-default. All gates must pass.
"""


# ==========================================================
# Allowed intents for auto-send
# ==========================================================

AUTO_SEND_ALLOWED_INTENTS = {
    "shipping_status",
    "firmware_update_info",
    "firmware_update",
}

AUTO_SEND_MIN_CONFIDENCE = 0.85


def classify_auto_send(
    *,
    latest_message: str,
    intent: str | None,
    intent_confidence: float,
    safety_mode: str,
    draft_text: str = "",
    acceptance_failures: list[str] | None = None,
    missing_information: dict | None = None,
) -> dict:
    """
    HARD deny-by-default auto-send classifier.

    ALL of these must be true:
      1. confidence >= AUTO_SEND_MIN_CONFIDENCE
      2. intent in AUTO_SEND_ALLOWED_INTENTS
      3. safety_mode == "safe"
      4. variable_verification.has_required_missing == false
      5. ambiguity_detected == false
      6. NOT multi-intent (no acceptance failures from multi-intent)

    Auto-send must NEVER trigger if required variables are missing.
    """

    acceptance_failures = acceptance_failures or []
    missing_information = missing_information or {}

    if not isinstance(draft_text, str):
        draft_text = ""

    # -------------------------------------------------
    # GATE 1: Safety mode — must be "safe"
    # -------------------------------------------------
    safety_norm = (safety_mode or "").lower().strip()
    if safety_norm != "safe":
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: safety_mode='{safety_norm}' (must be 'safe')",
        }

    # -------------------------------------------------
    # GATE 2: Intent must be in allowed list
    # -------------------------------------------------
    if intent not in AUTO_SEND_ALLOWED_INTENTS:
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: intent '{intent}' not eligible for auto-send",
        }

    # -------------------------------------------------
    # GATE 3: Confidence threshold
    # -------------------------------------------------
    if intent_confidence < AUTO_SEND_MIN_CONFIDENCE:
        return {
            "auto_send": False,
            "auto_send_reason": (
                f"Blocked: confidence {intent_confidence:.2f} < "
                f"{AUTO_SEND_MIN_CONFIDENCE:.2f}"
            ),
        }

    # -------------------------------------------------
    # GATE 4: Missing required variables (HARD BLOCK)
    # Check both missing_information items AND has_required_missing flag
    # -------------------------------------------------
    has_required_missing = missing_information.get("has_required_missing", False)
    if has_required_missing:
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: required variables are missing",
        }

    # Also check blocking items in missing_information
    items = missing_information.get("items") or []
    blocking_items = [
        i for i in items
        if isinstance(i, dict) and i.get("severity") == "blocking"
    ]
    if blocking_items:
        keys = [i.get("key", "unknown") for i in blocking_items]
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: missing required info {keys}",
        }

    # -------------------------------------------------
    # GATE 5: Ambiguity detected (HARD BLOCK)
    # Passed via missing_information dict or acceptance_failures
    # -------------------------------------------------
    ambiguity_detected = missing_information.get("ambiguity_detected", False)
    if ambiguity_detected:
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: ambiguity detected in classification",
        }

    # -------------------------------------------------
    # GATE 6: Multi-intent / acceptance failures (HARD BLOCK)
    # -------------------------------------------------
    if acceptance_failures:
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: acceptance gate failed",
        }

    # -------------------------------------------------
    # GATE 7: Draft contains question (safety check)
    # -------------------------------------------------
    if "?" in draft_text and intent != "firmware_update_info":
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: draft contains question",
        }

    # -------------------------------------------------
    # PASS — All gates cleared
    # -------------------------------------------------
    return {
        "auto_send": True,
        "auto_send_reason": (
            f"Eligible: intent='{intent}', confidence={intent_confidence:.2f}, "
            f"safety='{safety_norm}'"
        ),
    }
