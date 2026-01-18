from ai.auto_send_classifier import classify_auto_send


def evaluate_auto_send(
    message: str,
    intent: str | None,
    intent_confidence: float,
    safety_mode: str,
    draft_text,
    acceptance_failures=None,
    missing_information=None,
) -> dict:

    # HARD NORMALIZATION
    if isinstance(draft_text, dict):
        draft_text = draft_text.get("response_text", "")
    elif not isinstance(draft_text, str):
        draft_text = ""

    return classify_auto_send(
        latest_message=message,
        intent=intent,
        intent_confidence=intent_confidence,
        safety_mode=safety_mode,
        draft_text=draft_text,
        acceptance_failures=acceptance_failures or [],
        missing_information=missing_information or {},
    )
