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
    latest_message: str,
    intent: str,
    intent_confidence: float,
    safety_mode: str,
    missing_information: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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

    # -------------------------------------------------
    # GATE 5: Confidence threshold (fallback)
    # Only applies if NO phrase matched above.
    # -------------------------------------------------
    global_min_conf = float(rules.get("min_confidence", 1.0))
    intent_min_conf = float(cfg.get("min_confidence", global_min_conf))
    
    if intent_confidence < intent_min_conf:
        return {
            "auto_send": False,
            "auto_send_reason": (
                f"Blocked: confidence {intent_confidence:.2f} < threshold {intent_min_conf:.2f} "
                f"for '{intent}' (no phrase match)"
            ),
        }

    # -------------------------------------------------
    # ALL GATES PASSED (high confidence, no phrase needed)
    # -------------------------------------------------
    return {
        "auto_send": True,
        "auto_send_reason": (
            f"Eligible: intent='{intent}', confidence={intent_confidence:.2f}, "
            f"safety='{safety_mode_norm}'"
        ),
    }