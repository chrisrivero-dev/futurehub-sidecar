"""
Draft Generator
Responsible for generating agent-facing response drafts.
"""

from typing import List
import random
from ai.faq_index import load_faq_snippets
from ai.auto_send_evaluator import evaluate_auto_send


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
# SHIPPING STATUS — SAFE MICRO-VARIATION (OPTION 1)
# -------------------------------------------------
SHIPPING_OPENERS = [
    "I can help check on your order status.",
    "Happy to look into where things are in the shipping process.",
    "Let me help get you an update on your order.",
]

## ============================================================
# ## PHASE 1.4 — Knowledge Enrichment (HELPER, STUB)
# MUST live at module scope
# ============================================================

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
# ============================================================
# ## PHASE 3.1 — Reasoning Style Control (HELPER)
# ============================================================
def apply_reasoning_style(
    draft_text: str,
    intent: str | None,
    mode: str,
) -> str:
    """
    Control how much reasoning and explanation is allowed.
    Keeps drafts thoughtful but not verbose or speculative.
    """

    # Diagnostic replies should prefer questions over explanations
    if mode == "diagnostic":
        if "why this happens" in draft_text.lower():
            draft_text = draft_text.replace(
                "why this happens",
                "what we need to check next"
            )

    # Explanatory replies should not include troubleshooting steps
    if mode == "explanatory":
        forbidden = [
            "step",
            "check",
            "try",
            "restart",
            "reboot",
        ]
        for word in forbidden:
            if f"{word} " in draft_text.lower():
                draft_text = draft_text.replace(word, "")

    return draft_text
# ============================================================
# ## PHASE 4.1 — Generic Opener Detector (HELPER)
# ============================================================

GENERIC_OPENERS = [
    "thanks for the details",
    "thanks for reaching out",
    "let’s narrow this down",
    "lets narrow this down",
    "happy to help",
]

def has_generic_opener(draft_text: str) -> bool:
    if not draft_text:
        return True

    first_line = draft_text.strip().split("\n", 1)[0].lower()
    return any(opener in first_line for opener in GENERIC_OPENERS)


# ============================================================
# ## PHASE 4.2 — Draft Acceptance Gate (HARD)
# ============================================================

def draft_fails_acceptance_gate(
    draft_text: str,
    intent: str | None,
    mode: str,
) -> list[str]:
    """
    HARD stop rules.
    If this returns ANY failures → auto-send is forbidden.
    """

    failures: list[str] = []

    if not draft_text.strip():
        failures.append("empty_draft")

    # 1️⃣ Generic opener is NOT allowed for concrete intents
    if intent not in ("unknown_vague", None):
        if has_generic_opener(draft_text):
            failures.append("generic_opener")

    # 2️⃣ Diagnostic replies must ask something
    if mode == "diagnostic":
        if "?" not in draft_text:
            failures.append("diagnostic_no_questions")

    # 3️⃣ Explanatory replies must not include troubleshooting
    if mode == "explanatory":
        forbidden = ["step", "check", "try", "restart", "reboot"]
        lowered = draft_text.lower()
        if any(word in lowered for word in forbidden):
            failures.append("explanatory_contains_troubleshooting")

    return failures


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
# ============================================================
def generate_draft(
    message: str | None = None,
    latest_message: str | None = None,
    subject: str | None = None,
    intent: str | None = None,
    prior_agent_messages: List[str] | None = None,
    mode: str | None = None,
    tone_modifier: str | None = None,
    **kwargs,
) -> dict:
    print(">>> generate_draft loaded from:", __file__)
    print(">>> RAW PAYLOAD message:", message)
    print(">>> RAW PAYLOAD latest_message:", latest_message)

    text = (latest_message or "").strip()

    if not text and message:
        print("⚠️ Ignored legacy `message` field — latest_message required")

    prior_agent_messages = prior_agent_messages or []

    # ----------------------------
    # Phase 1.2 — mode derivation
    # ----------------------------
    if intent == "shipping_status":
        mode = "explanatory"
    elif intent in ("setup_help", "sync_delay", "not_hashing"):
        mode = "diagnostic"
    else:
        mode = mode or "diagnostic"

    print(">>> FINAL MODE:", mode)
    print(">>> FINAL INTENT:", intent)

    # ============================================================
    # ## PHASE 1.3 — Draft Differentiation by Intent (LOCAL HELPER, LOCKED)
    # ============================================================
    def _draft_for_intent(intent: str) -> str:
        print(">>> _draft_for_intent CALLED with intent =", intent)

        
        if intent == "setup_help":
            return (
                "Thanks for the details — that helps.\n\n"
                "Let’s walk through a few quick things to check:\n\n"
                "1) Make sure the Apollo is fully powered on and connected via Ethernet\n"
                "2) Confirm your computer is on the same network\n"
                "3) Try accessing the dashboard using the device’s IP address\n\n"
                "Let me know which step you get stuck on and we’ll go from there."
            )
        if intent == "diagnostic_generic":
            return (
                "I see what you’re describing.\n\n"
                "Based on what you’ve shared so far, the next step is to narrow down "
                "where things are getting stuck.\n\n"
                "Could you confirm:\n"
                "1) What the device is currently showing on the dashboard\n"
                "2) Whether this issue started recently or has been happening since setup\n"
            )


        if intent == "shipping_status":
            opener = random.choice(SHIPPING_OPENERS)
            return (
                f"{opener}\n\n"
                "Once I have a bit more detail, I’ll be able to point you in the right direction."
            )

        if intent == "unknown_vague":
            return (
                "Thanks for reaching out.\n\n"
                "Could you tell me a bit more about what you’re seeing or trying to do?\n"
                "A few extra details will help me guide you better."
            )

        # ----------------------------
        # Phase 2 — intent-safe fallback
        # ----------------------------
        return (
            "I see what you’re describing.\n\n"
            "Based on what you’ve shared so far, the next step is to narrow down "
            "where things are getting stuck.\n\n"
            "Could you confirm:\n"
            "1) What the device is currently showing on the dashboard\n"
            "2) Whether this issue started recently or has been happening since setup\n"
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
    # MODE + INTENT RESOLUTION
    # ----------------------------
    text_lower = text.lower()
    intent_locked = False


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
    # -------------------------------------------------
    # Phase 2 — intent guard (prevent setup_help overreach)
    # -------------------------------------------------
    if intent == "setup_help":
        setup_indicators = [
            "dashboard",
            "apollo.local",
            "ip address",
            "ethernet",
            "network",
            "wifi",
        ]
    # -------------------------------------------------
    # Phase 2 — intent guard for ambiguous diagnostics
    # -------------------------------------------------
    if intent == "unknown_vague":
        diagnostic_indicators = [
            "nothing",
            "not working",
            "doesn't work",
            "doesnt work",
            "not happening",
            "stuck",
            "ready",
            "synced",
        ]

        if any(indicator in text_lower for indicator in diagnostic_indicators):
            intent = "diagnostic_generic"
            intent_locked = True



    # -------------------------------------------------
    # Phase 2 — intent guard for ambiguous diagnostics
    # -------------------------------------------------
    if intent == "unknown_vague":
        diagnostic_indicators = [
            "nothing",
            "not working",
            "doesn't work",
            "doesnt work",
            "not happening",
            "stuck",
            "ready",
            "synced",
        ]

        if any(indicator in text_lower for indicator in diagnostic_indicators):
            intent = "diagnostic_generic"
            intent_locked = True

    # ----------------------------
    # Phase 2 — final draft intent (locked)
    # ----------------------------
    draft_intent = intent

    draft_text = _draft_for_intent(draft_intent)

    # -------------------------------------------------
    # PHASE 1.4 — knowledge enrichment hook (LOCKED)
    # -------------------------------------------------
    draft_text = enrich_with_knowledge(
        draft_text=draft_text,
        intent=intent,
        mode=mode,
    )
        # -------------------------------------------------
    # PHASE 3.1 — reasoning style enforcement
    # -------------------------------------------------
    draft_text = apply_reasoning_style(
        draft_text=draft_text,
        intent=intent,
        mode=mode,
    )


    # ----------------------------
    # Confidence (safe fallback)
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
        intent in ALLOWED_KNOWLEDGE_INTENTS
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

    draft_text = apply_draft_constraints(
        draft_text=draft_text,
        intent=intent,
        tone_modifier=tone_modifier,
    )
    # -------------------------------------------------
    # PHASE 4 — Acceptance Gate (HARD)
    # -------------------------------------------------
    failures = draft_fails_acceptance_gate(
        draft_text=draft_text,
        intent=intent,
        mode=mode,
    )

    if failures:
        return {
            "type": "requires_review",
            "response_text": draft_text,
            "quality_metrics": {
                "mode": mode,
                "delta_enforced": True,
                "acceptance_failures": failures,
            },
            "canned_response_suggestion": None,
        }

    return {
        "type": "full",
        "response_text": draft_text,
        "quality_metrics": {
            "mode": mode,
            "delta_enforced": True,
        },
        "canned_response_suggestion": None,
    }

# ============================================================
# ## PHASE 1.8 — Post-Generation Safety Constraints (HELPER)
# ============================================================

def apply_draft_constraints(
    draft_text: str,
    intent: str | None,
    tone_modifier: str | None,
) -> str:
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

    return draft_text
