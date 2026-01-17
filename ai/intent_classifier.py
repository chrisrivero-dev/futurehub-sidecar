"""
Intent Classifier
Lightweight heuristic classifier (placeholder for ML later)
"""

def classify_intent(message: str) -> str:
    if not message:
        return "unknown"

    msg = message.lower()

    if "refund" in msg or "return" in msg:
        return "billing_refund"
    if "firmware" in msg or "update" in msg:
        return "firmware_update"
    if "not working" in msg or "error" in msg:
        return "troubleshooting"
    if "shipping" in msg or "delivery" in msg:
        return "shipping_status"

    return "general_support"
