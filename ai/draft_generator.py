"""
Draft Generator
Responsible for generating agent-facing response drafts.
"""

from typing import List
from ai.faq_index import load_faq_snippets

# -------------------------------------------------
# PHASE 1.5 — knowledge gating rules (LOCKED)
# -------------------------------------------------
ALLOWED_KNOWLEDGE_INTENTS = {
    "setup_help",
    "shipping_status",
}

ALLOWED_KNOWLEDGE_MODES = {
    "explanatory",
}

MAX_KNOWLEDGE_CHARS = 600

# -------------------------------------------------
# PHASE 1.4 — knowledge enrichment (STUB ONLY)
# MUST live at module scope
# -------------------------------------------------
def enrich_with_knowledge(
    draft_text: str,
    intent: str,
    mode: str,
) -> str:
    """
    Phase 1.4 placeholder.
    Knowledge injection is disabled for now.
    """
    return draft_text
# -------------------------------------------------
# PHASE 1.6 — knowledge placement rules (LOCKED)
# -------------------------------------------------
KNOWLEDGE_PREPEND_INTENTS = {
    "shipping_status",
}

KNOWLEDGE_APPEND_INTENTS = {
    "setup_help",
    "not_hashing",
    "sync_delay",
}
# -------------------------------------------------
# PHASE 1.7 — confidence gating (LOCKED)
# -------------------------------------------------
MIN_KNOWLEDGE_CONFIDENCE = 0.65



# ============================================================
# PHASE 1.1 LOCKED — do not modify without tests
#
# Contract guarantees:
# - latest_message is the ONLY input used for draft text
# - legacy `message` field is ignored
# - mode is derived internally (not passed from app.py)
# - safe fallback behavior for unknown_vague intent
# ================================================
def generate_draft(
    message: str | None = None,
    latest_message: str | None = None,
    subject: str | None = None,
    intent: str | None = None,
    prior_agent_messages: List[str] | None = None,
    mode: str | None = None,
    tone_modifier: str | None = None,
    **kwargs,  # forward compatibility
) -> dict:
    print(">>> generate_draft loaded from:", __file__)
    print(">>> RAW PAYLOAD message:", message)
    print(">>> RAW PAYLOAD latest_message:", latest_message)

    # ----------------------------
    # Phase 1.1 — input lock
    # ----------------------------
    text = (latest_message or "").strip()

    if not text and message:
        print("⚠️ Ignored legacy `message` field — latest_message required")

    prior_agent_messages = prior_agent_messages or []
    # PHASE 1.2 LOCKED — intent → mode mapping stable

    # ----------------------------
    # Phase 1.2 — mode derivation (MUST live here)
    # ----------------------------
    if intent == "shipping_status":
        mode = "explanatory"
    elif intent in ("setup_help", "sync_delay", "not_hashing"):
        mode = "diagnostic"
    else:
        mode = mode or "diagnostic"

    print(">>> FINAL MODE:", mode)
    print(">>> FINAL INTENT:", intent)


    # ----------------------------
    # Draft generation continues below
    # (leave the rest of your logic unchanged)
    # ----------------------------
        # -------------------------------------------------
    # PHASE 1.3 — draft differentiation by intent (LOCKED)
    # -------------------------------------------------
    def _draft_for_intent(intent: str) -> str:
        if intent == "setup_help":
            return (
                "Thanks for the details — that helps.\n\n"
                "Let’s walk through a few quick things to check:\n\n"
                "1) Make sure the Apollo is fully powered on and connected via Ethernet\n"
                "2) Confirm your computer is on the same network\n"
                "3) Try accessing the dashboard using the device’s IP address\n\n"
                "Let me know which step you get stuck on and we’ll go from there."
            )

        if intent == "shipping_status":
            return (
                "Thanks for checking in — happy to help.\n\n"
                "I can help look into your order status and what to expect next.\n"
                "Once I have a bit more detail, I’ll be able to point you in the right direction."
            )

        if intent == "unknown_vague":
            return (
                "Thanks for reaching out.\n\n"
                "Could you tell me a bit more about what you’re seeing or trying to do?\n"
                "A few extra details will help me guide you better."
            )

        # Default fallback (existing behavior)
        return (
            "Thanks for the details — that helps.\n"
            "Let’s narrow this down with a few quick checks."
        )


    # ----------------------------
    # EARLY EXIT — no customer text
    # ----------------------------
    if not text:
        return {
            "type": "partial",
            "response_text": "I need more information from the customer before responding.",
            "quality_metrics": {
                "mode": mode,
                "delta_enforced": False,
            },
            "canned_response_suggestion": None,
        }

    # ----------------------------
    # MODE + INTENT RESOLUTION (AUTHORITATIVE)
    # ----------------------------
    text_lower = text.lower()

    if intent is None:
        if any(k in text_lower for k in ["order", "shipping", "ship", "tracking"]):
            intent = "shipping_status"
        elif any(k in text_lower for k in ["refund", "return", "chargeback"]):
            intent = "refund_policy"

    if mode is None:
        if intent == "shipping_status":
            mode = "explanatory"
        elif intent in ("refund_policy",):
            mode = "policy"
        else:
            mode = "diagnostic"

    print(">>> DRAFT MODE:", mode)
    print(">>> INTENT:", intent)
    # ----------------------------
    # MODE FINALIZATION (HARD RULE)
    # ----------------------------
    if intent == "shipping_status":
        mode = "explanatory"
    elif intent == "refund_policy":
        mode = "policy"
    elif mode is None:
        mode = "diagnostic"


    # ----------------------------
    # TONE DETECTION (TRUST EROSION)
    # ----------------------------
    effective_tone = (
        tone_modifier
        if tone_modifier is not None
        else (
            "panic"
            if any(
                k in text_lower
                for k in [
                    "ridiculous",
                    "next week",
                    "still nothing",
                    "nothing happened",
                    "you said",
                    "told me",
                ]
            )
            else "neutral"
        )
    )

    # ----------------------------
    # DRAFT BODY
    # ----------------------------
    parts: list[str] = []

    if mode == "diagnostic":
        parts.append("Thanks for the details — that helps.")
        parts.append("Let’s narrow this down with a few quick checks.")
        parts.append("Here are a couple things we can check next to narrow this down.")

    elif mode == "explanatory":
        if effective_tone == "panic":
            parts.append(
                "I understand how frustrating it is to keep hearing conflicting updates, "
                "and I want to be transparent about what we can and can’t confirm right now."
            )
        else:
            parts.append("Thanks for checking in.")

        parts.append("Tracking usually appears once the carrier scans the package.")
        parts.append(
            "If you’d like, share your order number and I can take a closer look for you."
        )



    elif mode == "guided_setup":
        parts.append("No worries — this is a very common first-time setup question.")
        parts.append("Let’s start by confirming the device is actually on your network.")
        parts.append(
            "Check your router’s connected devices list and see if the Apollo appears there."
        )
        parts.append(
            "If it does, try opening the IP address directly instead of apollo.local."
        )

    elif mode == "policy":
        parts.append("I can help explain how this works.")
        parts.append("Refunds involving crypto payments require manual review.")
        parts.append("An agent will review your order details and follow up with next steps.")

    else:
        parts.append("Thanks for reaching out.")
        parts.append("An agent will review your message and follow up shortly.")

    draft_text = _draft_for_intent(intent)
    # -------------------------------------------------
    # PHASE 1.4 — knowledge enrichment hook (LOCKED)
    # MUST be AFTER draft_text exists
    # -------------------------------------------------
    draft_text = enrich_with_knowledge(
        draft_text=draft_text,
        intent=intent,
        mode=mode,
    )
    # ----------------------------
    # Confidence (from classifier) — safe fallback
    # ----------------------------
    confidence = kwargs.get("confidence", {})
    intent_confidence = (
        confidence.get("intent_confidence", 0.0)
        if isinstance(confidence, dict)
        else 0.0
    )

    # -------------------------------------------------
    # PHASE 1.7 — confidence-aware knowledge injection (LOCKED)
    # -------------------------------------------------
    if (
        intent is not None
        and intent in ALLOWED_KNOWLEDGE_INTENTS
        and mode in ALLOWED_KNOWLEDGE_MODES
        and intent_confidence >= MIN_KNOWLEDGE_CONFIDENCE
    ):
        faq_snippets = load_faq_snippets(intent)

        if faq_snippets:
            block = "\n\n".join(f"- {s}" for s in faq_snippets)
            block = block[:MAX_KNOWLEDGE_CHARS]

            knowledge_block = (
                "Here’s some helpful information that may be useful:\n\n"
                + block
            )

            if intent in KNOWLEDGE_PREPEND_INTENTS:
                draft_text = knowledge_block + "\n\n" + draft_text
            else:
                draft_text = draft_text + "\n\n" + knowledge_block


    # -------------------------------------------------
    # PHASE 1.7 — confidence-aware knowledge injection (LOCKED)
    # -------------------------------------------------
    if (
        intent is not None
        and intent in ALLOWED_KNOWLEDGE_INTENTS
        and mode in ALLOWED_KNOWLEDGE_MODES
        and intent_confidence >= MIN_KNOWLEDGE_CONFIDENCE
    ):
        faq_snippets = load_faq_snippets(intent)

        if faq_snippets:
            block = "\n\n".join(f"- {s}" for s in faq_snippets)
            block = block[:MAX_KNOWLEDGE_CHARS]

            knowledge_block = (
                "Here’s some helpful information that may be useful:\n\n"
                + block
            )

            if intent in KNOWLEDGE_PREPEND_INTENTS:
                draft_text = knowledge_block + "\n\n" + draft_text
            else:
                draft_text = draft_text + "\n\n" + knowledge_block

    # ----------------------------
    # POST-GENERATION CONSTRAINTS
    # ----------------------------
    draft_text = apply_draft_constraints(
        draft_text=draft_text,
        intent=intent,
        tone_modifier=effective_tone,
    )

    return {
        "type": "full",
        "response_text": draft_text,
        "quality_metrics": {
            "mode": mode,
            "delta_enforced": True,
        },
        "canned_response_suggestion": None,
    }


def apply_draft_constraints(
    draft_text: str,
    intent: str | None,
    tone_modifier: str | None,
) -> str:
    """
    Enforce post-generation safety and trust constraints.
    This layer does NOT add new information — it only removes or reframes risky content.
    """

    if intent == "shipping_status" and tone_modifier == "panic":
        forbidden_phrases = [
            "within 2 hours",
            "within 4 hours",
            "3-5 business days",
            "delivery timeline",
            "typical Apollo shipping timeframes",
        ]

        for phrase in forbidden_phrases:
            draft_text = draft_text.replace(phrase, "").strip()

        if "frustrat" not in draft_text.lower():
            draft_text = (
                "I understand how frustrating it is to keep hearing conflicting updates, "
                "and I want to be transparent about what we can and can’t confirm right now.\n\n"
                + draft_text
            )

    return draft_text
