# File: utils/auto_send_evaluator.py

"""
Auto-send eligibility evaluator
Pure function - evaluates eligibility WITHOUT executing sends
Day 6: Evaluation only, no execution
"""

from typing import Dict, Any, Tuple, Optional
import logging

from intent_classifier import SAFE_INTENTS, UNSAFE_INTENTS

logger = logging.getLogger(__name__)

# Default confidence threshold for safe intents
CONFIDENCE_THRESHOLD = 0.88

# Explicit eligibility policy (advisory only; Freshdesk decides execution)
# NOTE: This does NOT send anything. It only marks eligibility.
AUTO_SEND_WHITELIST: Dict[str, Dict[str, Any]] = {
    "shipping_status": {
        "min_confidence": 0.88,
        "allow_partial": True,
    },
    "setup_help": {
        "min_confidence": 0.92,
        "allow_partial": True,
    },
    "firmware_update": {
        "min_confidence": 0.93,
        "allow_partial": False,
    },
}
# Backward compatibility for legacy tests
# Uses lowest configured whitelist threshold
CONFIDENCE_THRESHOLD = min(
    policy["min_confidence"] for policy in AUTO_SEND_WHITELIST.values()
)

def evaluate_auto_send_eligibility(
    intent: Optional[str],
    confidence: Optional[float],
    has_attachments: bool = False,
    has_logs: bool = False,
    ticket_status: str = "open",
) -> Tuple[bool, str]:
    """
    Evaluate if ticket is eligible for auto-send (pure function)

    This function ONLY evaluates eligibility - it does NOT execute sends.

    Args:
        intent: Classified intent from sidecar
        confidence: Confidence score (0.0-1.0)
        has_attachments: Whether ticket has attachments
        has_logs: Whether ticket contains log data
        ticket_status: Current ticket status

    Returns:
        Tuple of (eligible: bool, reason: str)
    """

    # Validation checks
    if intent is None:
        return False, "No intent classified"

    if confidence is None:
        return False, "No confidence score"

    # Optional: sanity guard (helps catch taxonomy drift)
    if intent not in SAFE_INTENTS and intent not in UNSAFE_INTENTS and intent not in AUTO_SEND_WHITELIST:
        return False, f"Intent '{intent}' unknown to evaluator"

    # Rule 1: Block unsafe intents immediately
    if intent in UNSAFE_INTENTS:
        return False, f"Intent '{intent}' is unsafe for auto-send"

    # Rule 2: Safe intents must meet default confidence threshold
    if confidence < CONFIDENCE_THRESHOLD:
        return False, f"Confidence {confidence:.2f} below threshold {CONFIDENCE_THRESHOLD:.2f}"

    # Rule 4: No attachments allowed
    if has_attachments:
        return False, "Ticket has attachments - requires human review"

    # Rule 5: No log data allowed
    if has_logs:
        return False, "Ticket contains log data - requires human review"

    # Rule 6: Only open tickets eligible
    if ticket_status != "open":
        return False, f"Ticket status '{ticket_status}' not eligible"

    # All checks passed
    return True, f"Eligible: {intent} with {confidence:.2%} confidence"


def extract_eligibility_factors(
    sidecar_response: Dict[str, Any],
    ticket_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract factors needed for eligibility evaluation from sidecar response

    Args:
        sidecar_response: Response data from sidecar service
        ticket_data: Ticket metadata (status, attachments, etc.)

    Returns:
        Dictionary with extracted factors
    """
    factors: Dict[str, Any] = {
        "intent": None,
        "confidence": None,
        "has_attachments": False,
        "has_logs": False,
        "ticket_status": "open",
    }

    # Extract from sidecar response
    if sidecar_response and isinstance(sidecar_response, dict):
        factors["intent"] = sidecar_response.get("intent")
        factors["confidence"] = sidecar_response.get("confidence")

        # Check analysis for log indicators
        analysis = sidecar_response.get("analysis", {})
        if isinstance(analysis, dict):
            key_entities = analysis.get("key_entities", [])
            if isinstance(key_entities, list):
                log_keywords = ["log", "crash", "error", "stacktrace", "debug"]
                factors["has_logs"] = any(
                    keyword in str(entity).lower()
                    for entity in key_entities
                    for keyword in log_keywords
                )

    # Extract from ticket data
    if ticket_data and isinstance(ticket_data, dict):
        factors["ticket_status"] = ticket_data.get("status", "open")
        factors["has_attachments"] = ticket_data.get("has_attachments", False)

        # Check description for log indicators
        description = ticket_data.get("description", "")
        if description:
            log_indicators = ["attached log", "see logs", "log file", "crash dump"]
            factors["has_logs"] = factors["has_logs"] or any(
                indicator in description.lower() for indicator in log_indicators
            )

    return factors


def evaluate_from_sidecar_response(
    sidecar_response: Dict[str, Any],
    ticket_data: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Convenience function: extract factors and evaluate eligibility

    Args:
        sidecar_response: Response data from sidecar service
        ticket_data: Ticket metadata

    Returns:
        Tuple of (eligible: bool, reason: str)
    """
    factors = extract_eligibility_factors(sidecar_response, ticket_data)

    return evaluate_auto_send_eligibility(
        intent=factors["intent"],
        confidence=factors["confidence"],
        has_attachments=factors["has_attachments"],
        has_logs=factors["has_logs"],
        ticket_status=factors["ticket_status"],
    )


def log_evaluation(ticket_id: int, eligible: bool, reason: str) -> None:
    """
    Log eligibility evaluation for audit trail

    Args:
        ticket_id: Ticket ID
        eligible: Whether ticket is eligible
        reason: Reason for eligibility decision
    """
    if eligible:
        logger.info(f"Ticket {ticket_id} eligible for auto-send: {reason}")
    else:
        logger.info(f"Ticket {ticket_id} NOT eligible for auto-send: {reason}")
