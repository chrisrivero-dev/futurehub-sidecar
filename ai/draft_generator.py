"""
Draft Generator
Responsible for generating agent-facing response drafts.
"""

def generate_draft(
    message: str | None = None,
    latest_message: str | None = None,
    subject: str | None = None,
    intent: str | None = None,
    prior_agent_messages: list[str] | None = None,
    mode: str | None = None,
    **kwargs,   # ← THIS IS THE KEY
) -> str:
    print(">>> generate_draft loaded from:", __file__)
    print(">>> generate_draft mode:", mode)

    text = message or latest_message

    if not text:
        return "I need more information from the customer before responding."

    prior_agent_messages = prior_agent_messages or []

    draft = (
        f"Thanks for reaching out.\n\n"
        f"I understand your message:\n"
        f"\"{text.strip()}\"\n\n"
        f"I’ll help you with this as quickly as possible."
    )

    if intent:
        draft += f"\n\n(Detected intent: {intent})"

    if mode:
        draft += f"\n\n[Mode: {mode}]"

    return draft

