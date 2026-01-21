# ai/fallback_router.py

from ai.fallback_prompts import FALLBACK_SYSTEM_PROMPTS


def classify_fallback_category(intent: str, message: str) -> str:
    """
    Coarse routing only.
    This does NOT override intent classification.
    It is used ONLY when canned responses fail.
    """

    text = message.lower()

    if intent == "refund" or "refund" in text or "return" in text:
        return "refund"

    if intent == "shipping" or "order" in text or "shipping" in text:
        return "shipping"

    if intent == "dashboard" or "access" in text or "dashboard" in text:
        return "access"

    if intent == "low_hashrate" or "hash" in text or "not hashing" in text:
        return "hardware"

    return "unknown"


def generate_fallback_response(
    *,
    intent: str,
    message: str,
    llm_generate_fn,
) -> str:
    """
    Generates a category-aware fallback using the LLM.
    """

    category = classify_fallback_category(intent, message)
    system_prompt = FALLBACK_SYSTEM_PROMPTS[category]

    return llm_generate_fn(
        system_prompt=system_prompt,
        user_message=message,
    )
