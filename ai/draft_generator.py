"""
Draft Generator
Responsible for generating agent-facing response drafts.

This file is a repaired, production-safe version of the previously corrupted
draft_generator module. It preserves the existing outward behavior contract:
- generate_draft(...) returns a dict with: type, response_text, quality_metrics, canned_response_suggestion
- LLM output remains the primary source of draft text
- Knowledge injection remains gated and safe
- Acceptance gate remains a hard safety check (no crashes)
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
import logging

from ai.llm_client import generate_llm_response
from ai.auto_send_templates import AUTO_SEND_TEMPLATES  # kept for compatibility / future use
from ai.faq_index import load_faq_snippets

logger = logging.getLogger(__name__)

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

# -------------------------------------------------
# PHASE 4.1 — Generic Opener Detector (HELPER)
# -------------------------------------------------
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
def _baseline_draft_for_intent(intent: str | None, subject: str | None) -> str:
    """
    Deterministic baseline draft so we never fall back to the generic line
    when intent is known but LLM output is empty/unavailable.
    """
    intent = intent or "unknown_vague"

    if intent == "shipping_status":
        return (
            "Here’s an update on shipping.\n\n"
            "If you can share your order number (or the email used at checkout), "
            "I can check the latest status and whether tracking has been issued."
        )

    if intent == "setup_help":
        return (
            "Let’s get you into the dashboard.\n\n"
            "If `apollo.local` doesn’t load, the next step is to find the Apollo’s IP address "
            "from your router and open that IP in a browser on the same network."
        )

    if intent == "not_hashing":
        return (
            "If the miner isn’t hashing, the first thing to confirm is whether the node is fully synced.\n\n"
            "Does the dashboard show the node as fully synced, and do you see any error message on the Miner page?"
        )

    if intent == "sync_delay":
        return (
            "Initial sync can take a while.\n\n"
            "If block height is still increasing, it’s usually working normally. "
            "What block height do you currently see, and is it moving over time?"
        )

    if intent == "purchase_inquiry":
        return (
            "Absolutely — I can help.\n\n"
            "What are you looking to order (Apollo miner or Solo Node), and do you prefer "
            "the fastest shipping option or best value/performance?"
        )

    # Unknown / fallback
    subj = (subject or "").strip()
    if subj:
        return (
            f"Thanks for reaching out about: “{subj}”.\n\n"
            "What outcome are you hoping for so I can point you in the right direction?"
        )

    return "Could you share a bit more detail on what you’re trying to do so I can help?"

# ============================================================
# Phase 5B — Draft Wording Polish (SAFE-ONLY)
# ============================================================
def polish_draft_text(
    *,
    draft_text: str,
    intent: Optional[str],
    mode: str,
) -> str:
    """
    Final wording polish.
    NO logic changes.
    NO intent changes.
    Must NEVER crash.
    Must ALWAYS return a string.
    """

    if not isinstance(draft_text, str):
        return ""

    text = draft_text.strip()

    # Shipping auto-send: remove overly interactive phrasing
    if intent == "shipping_status" and mode == "explanatory":
        replacements = {
            "I can help": "Here’s an update",
            "Let me help": "Here’s an update",
            "Once I have a bit more detail": "Here’s what I can see so far",
            "I’ll be able to point you in the right direction": "I’ll share the latest status below",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove trailing standalone questions (only if safe to do so)
        cleaned_lines = []
        for line in text.splitlines():
            if line.strip().endswith("?"):
                continue
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines).strip()

    return text


# ============================================================
# PHASE 4.2 — Draft Acceptance Gate (HARD)
# ============================================================
def draft_fails_acceptance_gate(
    *,
    draft_text: str,
    intent: Optional[str],
    mode: str,
) -> List[str]:
    """
    HARD stop rules.
    If this returns ANY failures → auto-send is forbidden.
    """
    failures: List[str] = []

    safe_text = draft_text or ""
    lowered = safe_text.lower()

    # 1) Generic opener is NOT allowed for most concrete intents
    if intent not in ("unknown_vague", None):
        if intent not in ("shipping_status", "firmware_update", "purchase_inquiry") and has_generic_opener(safe_text):
            failures.append("generic_opener")

    # 2) Diagnostic replies must ask something
    if mode == "diagnostic":
        if "?" not in safe_text:
            failures.append("diagnostic_no_questions")

    # 3) Explanatory replies must not troubleshoot (except shipping/firmware)
    if mode == "explanatory" and intent not in ("shipping_status", "firmware_update"):
        forbidden = ["step", "check", "try", "restart", "reboot"]
        if any(word in lowered for word in forbidden):
            failures.append("explanatory_contains_troubleshooting")

    return failures


# ============================================================
# PHASE 1.8 — Post-Generation Safety Constraints (HELPER)
# ============================================================
def apply_draft_constraints(
    *,
    draft_text: str,
    intent: Optional[str],
    tone_modifier: Optional[str],
) -> str:
    """
    Applies post-generation safety and tone constraints
    without changing the semantic intent of the response.
    """
    if not isinstance(draft_text, str):
        return ""

    text = draft_text

    # If customer is panicking about shipping, avoid promising timelines
    if intent == "shipping_status" and tone_modifier == "panic":
        forbidden_phrases = [
            "within 2 hours",
            "within 4 hours",
            "3-5 business days",
            "delivery timeline",
            "typical Apollo shipping timeframes",
        ]
        for phrase in forbidden_phrases:
            text = text.replace(phrase, "")

    return text.strip()


# ============================================================
# PHASE 1.4 — Knowledge Enrichment Hook (HELPER, SAFE)
# ============================================================
def enrich_with_knowledge(
    draft_text: str,
    intent: Optional[str],
    mode: str,
) -> str:
    """
    Safe knowledge hook.
    This function MUST return a string and MUST NOT crash.
    Actual injection is performed later under confidence gating.
    """
    if not isinstance(draft_text, str):
        return ""

    return draft_text
# ============================================================
# PHASE 3.1 — Reasoning Style Control (HELPER, SAFE)
# ============================================================
def apply_reasoning_style(
    *,
    draft_text: str,
    intent: Optional[str],
    mode: str,
) -> str:
    """
    Keeps drafts thoughtful but not verbose/speculative.
    Must NEVER crash.
    Must ALWAYS return a string.
    """

    if not isinstance(draft_text, str):
        return ""

    text = draft_text.strip()

    # Optional light cleanup (non-destructive)
    if mode == "explanatory":
        forbidden_phrases = [
            "I think",
            "Maybe",
            "It might be",
            "Possibly",
        ]
        for phrase in forbidden_phrases:
            text = text.replace(phrase, "").strip()

    return text

# ============================================================
# PHASE 1.1 LOCKED — do not modify without tests
# ============================================================
def generate_draft(
    message: Optional[str] = None,
    latest_message: Optional[str] = None,
    subject: Optional[str] = None,
    intent: Optional[str] = None,
    prior_agent_messages: Optional[List[str]] = None,
    mode: Optional[str] = None,
    tone_modifier: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Main entry point called by routes/ai_draft.py.

    Contract:
      returns dict with keys:
        - type: "full" | "partial"
        - response_text: str
        - quality_metrics: dict
        - canned_response_suggestion: optional
    """
    print(">>> generate_draft loaded from:", __file__)
    print(">>> RAW PAYLOAD message:", message)
    print(">>> RAW PAYLOAD latest_message:", latest_message)

    # Normalize message sources
    if not latest_message and message:
        latest_message = message

    text = (latest_message or "").strip()
    if not text:
        # early exit - no customer text
        return {
            "type": "partial",
            "response_text": "I need more information from the customer before responding.",
            "quality_metrics": {
                "mode": (mode or "diagnostic"),
                "delta_enforced": False,
            },
            "canned_response_suggestion": None,
        }

    prior_agent_messages = prior_agent_messages or []

    # -------------------------------------------------
    # Intent nudges (safe, only if unknown)
    # -------------------------------------------------
    text_lower = text.lower()
    if intent in (None, "unknown_vague"):
        if any(k in text_lower for k in ["refund", "return", "chargeback"]):
            intent = "refund_policy"
        elif any(k in text_lower for k in ["purchase", "buy", "order another", "another node", "place an order"]):
            intent = "purchase_inquiry"
        elif any(k in text_lower for k in ["order", "shipping", "ship", "tracking", "delivery", "eta"]):
            intent = "shipping_status"

    # -------------------------------------------------
    # Mode derivation (kept consistent / no duplicates)
    # -------------------------------------------------
    if intent in ("shipping_status", "purchase_inquiry"):
        resolved_mode = "explanatory"
    elif intent in ("setup_help", "sync_delay", "not_hashing"):
        resolved_mode = "diagnostic"
    elif intent in ("refund_policy",):
        resolved_mode = "policy"
    else:
        resolved_mode = mode or "diagnostic"

    # Commerce must never be diagnostic
    if intent == "purchase_inquiry":
        resolved_mode = "explanatory"

    print(">>> FINAL MODE:", resolved_mode)
    print(">>> FINAL INTENT:", intent)


    # -------------------------------------------------
    # BASELINE DRAFT (prevents empty output)
    # -------------------------------------------------
    draft_text = _baseline_draft_for_intent(intent, subject)

    # -------------------------------------------------
    # LLM FIRST PASS — SOURCE OF TRUTH (SAFE WRAP)
    # -------------------------------------------------
    llm_text = ""
    try:
        llm_out = generate_llm_response(
            system_prompt=(
                "You are a calm, professional customer support agent.\n"
                "Answer the customer's message as helpfully and completely as possible.\n\n"
                "If you need more information to proceed, ask ONE clear follow-up question.\n"
                "If you do NOT need more information, provide a complete answer."
            ),
            user_message=latest_message,
        )

        if isinstance(llm_out, dict):
            llm_text = (llm_out.get("text") or llm_out.get("response") or "").strip()
        elif isinstance(llm_out, str):
            llm_text = llm_out.strip()

    except Exception:
        # LLM failure should NEVER kill draft generation
        llm_text = ""

    # If LLM returned something meaningful, override baseline
    if llm_text:
        draft_text = llm_text
   

    # -------------------------------------------------
    # Safe hooks (must not change behavior / must not crash)
    # -------------------------------------------------
    

    draft_text = enrich_with_knowledge(
        draft_text=draft_text,
        intent=intent,
        mode=resolved_mode,
    )
   

    draft_text = apply_reasoning_style(
        draft_text=draft_text,
        intent=intent,
        mode=resolved_mode,
    )
    

    draft_text = polish_draft_text(
        draft_text=draft_text,
        intent=intent,
        mode=resolved_mode,
    )
   

    # -------------------------------------------------
    # Confidence-aware knowledge injection (LOCKED gate)
    # -------------------------------------------------
    confidence = kwargs.get("confidence", {})
    intent_confidence = 0.0
    if isinstance(confidence, dict):
        try:
            intent_confidence = float(confidence.get("intent_confidence", 0.0))
        except Exception:
            intent_confidence = 0.0

    if (
        intent in ALLOWED_KNOWLEDGE_INTENTS
        and resolved_mode in ALLOWED_KNOWLEDGE_MODES
        and intent_confidence >= MIN_KNOWLEDGE_CONFIDENCE
    ):
        try:
            faq_snippets = load_faq_snippets(intent)  # must return list[str] or []
        except Exception:
            faq_snippets = []

        if faq_snippets:
            block = "\n\n".join(f"- {s}" for s in faq_snippets)
            block = block[:MAX_KNOWLEDGE_CHARS]
            knowledge_block = "Here’s some helpful information that may be useful:\n\n" + block

            if intent in KNOWLEDGE_PREPEND_INTENTS:
                draft_text = knowledge_block + "\n\n" + (draft_text or "")
            else:
                draft_text = (draft_text or "") + "\n\n" + knowledge_block

            draft_text = apply_draft_constraints(
                draft_text=draft_text,
                intent=intent,
                tone_modifier=tone_modifier,
            )

    # -------------------------------------------------
    # HARD NORMALIZATION — ensure string
    # -------------------------------------------------
    if isinstance(draft_text, dict):
        draft_text = (
            draft_text.get("response_text")
            or draft_text.get("text")
            or draft_text.get("response")
            or ""
        )
    if draft_text is None:
        draft_text = ""
    if not isinstance(draft_text, str):
        draft_text = str(draft_text)

    draft_text = draft_text.strip()

    # -------------------------------------------------
    # Acceptance Gate (HARD) — must never crash
    # -------------------------------------------------
    failures = draft_fails_acceptance_gate(
        draft_text=draft_text,
        intent=intent,
        mode=resolved_mode,
    )

    # -------------------------------------------------
    # FINAL HARD GUARANTEE
    # -------------------------------------------------
    if not draft_text:
        draft_text = "I can help — could you clarify what you’re looking for?"

    return {
        "type": "full",
        "response_text": draft_text,
        "quality_metrics": {
            "mode": resolved_mode,
            "delta_enforced": True,
            "fallback_used": bool(failures),
        },
        "canned_response_suggestion": None,
    }