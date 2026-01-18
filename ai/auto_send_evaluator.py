from ai.auto_send_classifier import classify_auto_send


def evaluate_auto_send(
    message: str,
    intent: str | None,
    intent_confidence: float,
    safety_mode: str,
    missing_information: dict | None = None,
) -> dict:
    """
    Central auto-send evaluation wrapper.
    Delegates rule logic to classify_auto_send().
    """

    return classify_auto_send(
        latest_message=message,
        intent=intent,
        intent_confidence=intent_confidence,
        safety_mode=safety_mode,
        missing_information=missing_information or {},
    )
