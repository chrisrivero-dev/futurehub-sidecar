import json
import os
from typing import Any, Dict, List, Optional


_RULES_CACHE: Optional[Dict[str, Any]] = None


def _load_rules() -> Dict[str, Any]:
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    here = os.path.dirname(os.path.abspath(__file__))
    rules_path = os.path.join(here, "auto_send_rules.json")

    with open(rules_path, "r", encoding="utf-8") as f:
        _RULES_CACHE = json.load(f)

    return _RULES_CACHE


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
    Returns ONLY:
      - auto_send (bool)
      - auto_send_reason (str)
    """

    # ----------------------------
    # HARD NORMALIZATION (CRITICAL)
    # ----------------------------
    if not isinstance(draft_text, str):
        draft_text = ""

    acceptance_failures = acceptance_failures or []
    missing_information = missing_information or {}

    """
    Determine auto-send eligibility.
    
    Logic order (MANDATORY):
      1. Safety gate
      2. Intent config + enabled check
      3. Missing blocking info gate
      4. Phrase-match override (bypasses confidence)
      5. Confidence threshold (fallback only)
    
    Returns:
      {
        "auto_send": bool,
        "auto_send_reason": str
      }
    """
    rules = _load_rules()

    msg = (latest_message or "").lower().strip()
    safety_mode_norm = (safety_mode or "").lower().strip()

    # -------------------------------------------------
    # GATE 1: Safety mode (hard block)
    # -------------------------------------------------
    allowed_safety = set(rules.get("allowed_safety_modes") or [])
    if allowed_safety and safety_mode_norm not in allowed_safety:
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: safety_mode='{safety_mode_norm}' not in allowed list",
        }

    # -------------------------------------------------
    # GATE 2: Intent must be configured and enabled
    # -------------------------------------------------
    intents_cfg = rules.get("intents") or {}
    cfg = intents_cfg.get(intent)
    
    if not cfg:
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: intent '{intent}' not configured for auto-send",
        }

    if not bool(cfg.get("enabled", False)):
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: intent '{intent}' auto-send disabled",
        }

    # -------------------------------------------------
    # GATE 3: Missing blocking info (hard block)
    # Must run BEFORE phrase match — if required info is
    # missing, we cannot auto-send regardless of phrase.
    # -------------------------------------------------
    blocking_keys: List[str] = list(cfg.get("required_missing_keys_blocking") or [])
    if blocking_keys and isinstance(missing_information, dict):
        items = missing_information.get("items") or []
        missing_keys = {i.get("key") for i in items if isinstance(i, dict)}
        required_missing = [k for k in blocking_keys if k in missing_keys]
        if required_missing:
            return {
                "auto_send": False,
                "auto_send_reason": f"Blocked: missing required info {required_missing}",
            }

    # -------------------------------------------------
    # GATE 4: Phrase-match override (BYPASSES CONFIDENCE)
    # If any configured phrase matches, approve immediately.
    # This allows low-confidence but clear phrase matches.
    # -------------------------------------------------
    phrases: List[str] = list(cfg.get("phrases") or [])
    
    for phrase in phrases:
        if not isinstance(phrase, str) or not phrase.strip():
            continue
        if phrase.lower() in msg:
            return {
                "auto_send": True,
                "auto_send_reason": f"Eligible: phrase match '{phrase}' for intent '{intent}'",
            }

  # ============================================================
# Phase 5A — Auto-Send Eligibility Gate (HARD)
# ============================================================

AUTO_SEND_ALLOWED_INTENTS = {
    "shipping_status",
}

AUTO_SEND_MIN_CONFIDENCE = 0.85


def classify_auto_send(
    *,
    latest_message: str,
    intent: str | None,
    intent_confidence: float,
    safety_mode: str,
    draft_text: str,
    acceptance_failures: list[str] | None = None,
    missing_information: dict | None = None,
) -> dict:
    """
    HARD deny-by-default auto-send classifier.
    Contract:
      Returns {
        "auto_send": bool,
        "auto_send_reason": str
      }
    """

    acceptance_failures = acceptance_failures or []
    missing_information = missing_information or {}

    # ----------------------------
    # Gate 1 — Acceptance gate MUST pass
    # ----------------------------
    if acceptance_failures:
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: acceptance gate failed",
        }

    # ----------------------------
    # Gate 2 — Intent allowlist
    # ----------------------------
    if intent not in AUTO_SEND_ALLOWED_INTENTS:
        return {
            "auto_send": False,
            "auto_send_reason": f"Blocked: intent '{intent}' not eligible",
        }

    # ----------------------------
    # Gate 3 — Safety mode
    # ----------------------------
    if safety_mode != "safe":
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: unsafe content",
        }

    # ----------------------------
    # Gate 4 — Confidence threshold
    # ----------------------------
    if intent_confidence < AUTO_SEND_MIN_CONFIDENCE:
        return {
            "auto_send": False,
            "auto_send_reason": (
                f"Blocked: confidence {intent_confidence:.2f} < {AUTO_SEND_MIN_CONFIDENCE:.2f}"
            ),
        }

    # ----------------------------
    # Gate 5 — Questions are NOT allowed
    # ----------------------------
    if "?" in draft_text:
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: draft contains question",
        }

    # ----------------------------
    # Gate 6 — Diagnostic language NOT allowed
    # ----------------------------
    forbidden_words = [
        "check",
        "try",
        "restart",
        "reboot",
        "confirm",
        "step",
        "troubleshoot",
    ]

    lowered = draft_text.lower()
    if any(word in lowered for word in forbidden_words):
        return {
            "auto_send": False,
            "auto_send_reason": "Blocked: diagnostic language detected",
        }

    # ----------------------------
    # PASS — Auto-send allowed
    # ----------------------------
    return {
        "auto_send": True,
        "auto_send_reason": (
            f"Eligible: intent='{intent}', confidence={intent_confidence:.2f}"
        ),
    }
