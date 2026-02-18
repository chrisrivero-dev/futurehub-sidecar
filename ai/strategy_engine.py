"""
Strategy Engine — Decision Engine for draft strategy selection.
Returns exactly one strategy per ticket based on intent, confidence, risk, and missing variables.

Strategies:
  AUTO_TEMPLATE  — High confidence, safe intent, template match exists. No LLM needed.
  PROACTIVE_DRAFT — Moderate+ confidence, safe/diagnostic. LLM or rule-based draft.
  ADVISORY_ONLY  — Low confidence or unsafe. Show guidance, no sendable draft.
  SCAFFOLD       — Unknown/vague intent. Provide skeleton for agent to complete.
"""

from typing import Any, Dict, List, Optional


# -----------------------------------------------------------
# Strategy constants
# -----------------------------------------------------------
AUTO_TEMPLATE = "AUTO_TEMPLATE"
PROACTIVE_DRAFT = "PROACTIVE_DRAFT"
ADVISORY_ONLY = "ADVISORY_ONLY"
SCAFFOLD = "SCAFFOLD"

# -----------------------------------------------------------
# Intent-to-template mapping (must match canned_responses.json ids)
# -----------------------------------------------------------
TEMPLATE_INTENT_MAP: Dict[str, str] = {
    "shipping_status": "4",       # "Shipping Status / Delays"
    "firmware_update": "1",       # "Firmware Update Instructions"
    "setup_help": "11",           # "Mining Pool Configuration" / setup
    "sync_delay": "2",            # "Node Sync Behavior"
    "not_hashing": "7",           # "Low or Zero Hashrate"
    "warranty_rma": "3",          # "Warranty Claim Information"
    "purchase_inquiry": "9",      # "Payment Verification"
}

# Intents that are safe for auto-template when confidence is high
AUTO_TEMPLATE_INTENTS = {
    "shipping_status",
    "firmware_update",
    "firmware_update_info",
    "setup_help",
    "purchase_inquiry",
}

# Intents that should never produce a sendable draft without review
ADVISORY_ONLY_INTENTS = {
    "performance_issue",
}

# -----------------------------------------------------------
# Confidence thresholds
# -----------------------------------------------------------
HIGH_CONFIDENCE = 0.85
MODERATE_CONFIDENCE = 0.60
LOW_CONFIDENCE = 0.40


def select_strategy(
    *,
    intent: str,
    confidence: float,
    safety_mode: str,
    missing_info: Optional[Dict[str, Any]] = None,
    ambiguity_detected: bool = False,
) -> Dict[str, Any]:
    """
    Select exactly one strategy based on ticket signals.

    Returns:
        {
            "strategy": "AUTO_TEMPLATE" | "PROACTIVE_DRAFT" | "ADVISORY_ONLY" | "SCAFFOLD",
            "reason": str,
            "template_id": str | None,  # only for AUTO_TEMPLATE
        }
    """
    missing_info = missing_info or {}
    blocking_count = missing_info.get("summary", {}).get("blocking_count", 0)
    safety = (safety_mode or "").lower().strip()

    # -----------------------------------------------------------
    # Gate 1: Unknown / vague intent → SCAFFOLD
    # -----------------------------------------------------------
    if intent in ("unknown_vague", "diagnostic_generic", None, ""):
        return {
            "strategy": SCAFFOLD,
            "reason": f"Intent '{intent}' is vague or unknown; providing scaffold for agent",
            "template_id": None,
        }

    # -----------------------------------------------------------
    # Gate 2: Advisory-only intents → ADVISORY_ONLY
    # -----------------------------------------------------------
    if intent in ADVISORY_ONLY_INTENTS:
        return {
            "strategy": ADVISORY_ONLY,
            "reason": f"Intent '{intent}' requires manual agent review",
            "template_id": None,
        }

    # -----------------------------------------------------------
    # Gate 3: Low confidence → SCAFFOLD
    # -----------------------------------------------------------
    if confidence < LOW_CONFIDENCE:
        return {
            "strategy": SCAFFOLD,
            "reason": f"Confidence {confidence:.2f} below threshold {LOW_CONFIDENCE}",
            "template_id": None,
        }

    # -----------------------------------------------------------
    # Gate 4: Unsafe + blocking missing info → ADVISORY_ONLY
    # -----------------------------------------------------------
    if safety not in ("safe", "explanatory") and blocking_count > 0:
        return {
            "strategy": ADVISORY_ONLY,
            "reason": f"Safety mode '{safety}' with {blocking_count} blocking missing field(s)",
            "template_id": None,
        }

    # -----------------------------------------------------------
    # Gate 5: High confidence + safe + template exists → AUTO_TEMPLATE
    # -----------------------------------------------------------
    if (
        confidence >= HIGH_CONFIDENCE
        and safety in ("safe", "explanatory")
        and intent in AUTO_TEMPLATE_INTENTS
        and intent in TEMPLATE_INTENT_MAP
        and not ambiguity_detected
    ):
        return {
            "strategy": AUTO_TEMPLATE,
            "reason": f"High confidence ({confidence:.2f}), safe, template available for '{intent}'",
            "template_id": TEMPLATE_INTENT_MAP[intent],
        }

    # -----------------------------------------------------------
    # Gate 6: Moderate+ confidence → PROACTIVE_DRAFT
    # -----------------------------------------------------------
    if confidence >= MODERATE_CONFIDENCE:
        return {
            "strategy": PROACTIVE_DRAFT,
            "reason": f"Moderate confidence ({confidence:.2f}), generating proactive draft",
            "template_id": TEMPLATE_INTENT_MAP.get(intent),
        }

    # -----------------------------------------------------------
    # Gate 7: Ambiguity or low-moderate confidence → SCAFFOLD
    # -----------------------------------------------------------
    if ambiguity_detected:
        return {
            "strategy": SCAFFOLD,
            "reason": "Ambiguity detected in customer intent",
            "template_id": None,
        }

    # -----------------------------------------------------------
    # Default: ADVISORY_ONLY
    # -----------------------------------------------------------
    return {
        "strategy": ADVISORY_ONLY,
        "reason": f"No strategy gates matched; defaulting to advisory (confidence={confidence:.2f})",
        "template_id": None,
    }
