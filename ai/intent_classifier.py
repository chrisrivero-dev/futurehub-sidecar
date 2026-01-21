"""
Intent Classifier
Lightweight heuristic classifier (placeholder for ML later)
"""

from typing import Optional


def classify_intent(message: Optional[str]) -> str:
    """
    Classify a customer message into a primary intent string.

    NOTE:
    - This is a heuristic classifier used by detect_intent().
    - Keep rules explicit and ordered.
    """

    if not message:
        return "unknown"

    msg = message.lower().strip()

    # -------------------------------------------------
    # Billing / Refunds
    # -------------------------------------------------
    if "refund" in msg or "return" in msg:
        return "billing_refund"

    # -------------------------------------------------
    # Firmware — split UPDATE vs ISSUE
    # -------------------------------------------------
    if "firmware" in msg or "update" in msg:
        update_phrases = [
            "how do i update",
            "how to update",
            "update the firmware",
            "firmware update",
            "upgrade firmware",
            "install firmware",
        ]

        if any(phrase in msg for phrase in update_phrases):
            return "firmware_update"

        # Default firmware path = issue/problem
        return "firmware_issue"

    # -------------------------------------------------
    # Troubleshooting / Errors
    # -------------------------------------------------
    if "not working" in msg or "error" in msg or "issue" in msg:
        return "troubleshooting"

    # -------------------------------------------------
    # Shipping / Delivery
    # -------------------------------------------------
    if "shipping" in msg or "delivery" in msg or "where is my order" in msg:
        return "shipping_status"

    # -------------------------------------------------
    # Fallback
    # -------------------------------------------------
    return "general_support"
