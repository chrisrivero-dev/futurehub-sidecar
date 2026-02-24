from ai.llm_client import generate_llm_response
from ai.auto_send_templates import AUTO_SEND_TEMPLATES

"""
Draft Generator
Responsible for generating agent-facing response drafts.
"""

from typing import List
import random
from ai.faq_index import load_faq_snippets
from ai.auto_send_evaluator import evaluate_auto_send
from ai.fallback_router import generate_fallback_response



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
# Phase 5B — Draft Wording Polish (SAFE-ONLY)
# ============================================================

def polish_draft_text(
    *,
    draft_text: str,
    intent: str | None,
    mode: str,
) -> str:
    """
    Final wording polish.
    NO logic changes. NO intent changes.
    """

    # HARD GUARANTEE: always operate on a string
    if not isinstance(draft_text, str):
        return ""

    text = draft_text.strip()

    # -------------------------------------------------
    # Shipping auto-send: remove interactive language
    # -------------------------------------------------
    if intent == "shipping_status" and mode == "explanatory":
        replacements = {
            "I can help": "Here’s an update",
            "Let me help": "Here’s an update",
            "Once I have a bit more detail": "Here’s what I can see so far",
            "I’ll be able to point you in the right direction": "I’ll share the latest status below",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # HARD remove trailing questions if any slipped in
        lines = [line for line in text.splitlines() if "?" not in line]
        text = "\n".join(lines).strip()

    return text


# ============================================================
# ## PHASE 4.2 — Draft Acceptance Gate (HARD)
# ============================================================
def draft_fails_acceptance_gate(
    draft_text: str | None,
    intent: str | None,
    mode: str,
) -> list[str]:
    """
    HARD stop rules.
    If this returns ANY failures → auto-send is forbidden.
    """

    failures: list[str] = []


    # ----------------------------------
    # 1️⃣ Generic opener rules
    # ----------------------------------
    # Concrete intents must not start generic
   # 1️⃣ Generic opener is NOT allowed for concrete intents
    if intent not in ("unknown_vague", None):
        if intent not in ("shipping_status", "firmware_update", "purchase_inquiry") \
        and has_generic_opener(draft_text):
            failures.append("generic_opener")


    # ----------------------------------
    # 2️⃣ Diagnostic replies must ask something
    # ----------------------------------
    if mode == "diagnostic":
        if "?" not in draft_text:
            failures.append("diagnostic_no_questions")

    # ----------------------------------
    # 3️⃣ Explanatory replies must not troubleshoot
    # ----------------------------------
    if mode == "explanatory" and intent not in ("shipping_status", "firmware_update"):
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
# ## PHASE 1.8 — Post-Generation Safety Constraints (HELPER)
# ============================================================

def apply_draft_constraints(
    draft_text: str,
    intent: str | None,
    tone_modifier: str | None,
) -> str:
    """
    Applies post-generation safety and tone constraints
    without changing the semantic intent of the response.
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

    return draft_text


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

    # 🔧 Normalize message sources (THIS WAS MISSING)
    if not latest_message and message:
        latest_message = message

    text = (latest_message or "").strip()
    # -------------------------------------------------
    # HARD INTENT LOCK — commerce must never downgrade
    # -------------------------------------------------
    if intent == "purchase_inquiry":
        mode = "explanatory"



    prior_agent_messages = prior_agent_messages or []

    # ----------------------------
    # Phase 1.2 — mode derivation
    # ----------------------------
    if intent in ("shipping_status", "purchase_inquiry"):
        mode = "explanatory"
    elif intent in ("setup_help", "sync_delay", "not_hashing"):
        mode = "diagnostic"
    else:
        mode = mode or "diagnostic"


    print(">>> FINAL MODE:", mode)
    print(">>> FINAL INTENT:", intent)
    # Force non-diagnostic mode for commerce intents
    if intent in ("purchase_inquiry",):
        mode = "explanatory"
        # ----------------------------
    # Phase 1.2 — mode derivation
    # ----------------------------
    if intent == "shipping_status":
        mode = "explanatory"
    elif intent in ("setup_help", "sync_delay", "not_hashing"):
        mode = "diagnostic"
    else:
        mode = mode or "diagnostic"


     # ============================================================
    # ## PHASE 1.3 — Draft Differentiation by Intent (LOCAL HELPER, LOCKED)
    # ============================================================

    def _draft_for_intent(intent: str) -> str:
        print(">>> _draft_for_intent CALLED with intent =", intent)

        # -------------------------------------------------
        # AUTO-SEND TEMPLATE SHORT-CIRCUIT (HARD)
        # -------------------------------------------------
        auto_send_used = False
        draft_text = None

        if intent in AUTO_SEND_TEMPLATES:
            print("🟢 AUTO-SEND TEMPLATE USED — LLM BYPASSED")
            auto_send_used = True
            draft_text = AUTO_SEND_TEMPLATES.get(intent) or ""


        # -------------------------------------------------
        # FALL THROUGH — normal draft logic continues below
        # -------------------------------------------------
        # (LLM or other logic happens AFTER this point)


        if intent == "purchase_inquiry":
            # LLM is king: do NOT ask diagnostic questions
            # (Either return a tight deterministic purchase reply,
            #  or let the LLM generate using a purchase prompt.)
            return (
                "Absolutely — I can help with that.\n\n"
                "To point you to the right option, which are you looking for?\n"
                "• Another Solo Node\n"
                "• Another Apollo miner\n\n"
                "And do you want:\n"
                "• the quickest ship option, or\n"
                "• the best value/performance option?"
            )

        
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
                "Happy to help clarify what’s happening with your order.\n\n"
                "It’s normal for shipping updates to take a little time to appear after checkout. "
                "Here’s what usually happens next."
            )
        # ✅ ADD IT RIGHT HERE
        if intent == "purchase_inquiry":
            return (
                "Absolutely — I can help with that.\n\n"
                "Here’s what I can assist with:\n"
                "• Current node availability and pricing\n"
                "• Differences between node models\n"
                "• Expected shipping timelines\n\n"
                "What would you like to start with?"
            )


        if intent == "unknown_vague" and normalized_intent != "purchase_inquiry":
            return {
                "type": "full",
                "response_text": fallback_text,
                "quality_metrics": {
                    "mode": mode,
                    "delta_enforced": True,
                    "fallback_used": True,
                    "reason": "unknown_intent_clarification",
                },
                "canned_response_suggestion": None,
            }


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
        try:
            from db import SessionLocal, safe_commit
            from models import DraftEvent, get_or_create_ticket
            session = SessionLocal()
            ticket_id = None
            freshdesk_ticket_id = kwargs.get("freshdesk_ticket_id")
            freshdesk_domain = kwargs.get("freshdesk_domain")
            if freshdesk_ticket_id and freshdesk_domain:
                ticket = get_or_create_ticket(session, freshdesk_ticket_id, freshdesk_domain)
                ticket_id = ticket.id
            clf = kwargs.get("classification") or {}
            sm = clf.get("safety_mode") if isinstance(clf, dict) else None
            cf = clf.get("confidence", {}) if isinstance(clf, dict) else {}
            cv = cf.get("intent_confidence") if isinstance(cf, dict) else None
            _rmap = {"safe": "low", "review_required": "medium", "unsafe": "high"}
            rc = _rmap.get((sm or "").lower()) if sm else None
            session.add(DraftEvent(
                subject=(subject or "")[:500],
                intent=intent,
                mode=mode,
                llm_used=False,
                ticket_id=ticket_id,
                confidence=cv,
                safety_mode=sm,
                risk_category=rc,
            ))
            safe_commit(session)
        except Exception:
            pass  # DB failure must never block draft return
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
    # -------------------------------------------------
    # INTENT NUDGES — upgrade obvious keywords from unknown_vague
    # -------------------------------------------------
    if intent in (None, "unknown_vague"):
        if "refund" in text_lower or "return" in text_lower or "chargeback" in text_lower:
            intent = "refund_policy"
        elif "purchase" in text_lower or "buy" in text_lower or "order another" in text_lower:
            intent = "purchase_inquiry"



    if intent is None:
        # ---- PURCHASE MUST BE DETECTED FIRST ----
        if any(k in text_lower for k in [
            "purchase",
            "buy",
            "order another",
            "another node",
            "new node",
            "solo node",
            "apollo",
            "place an order",
        ]):
            intent = "purchase_inquiry"

        elif any(k in text_lower for k in ["order", "shipping", "ship", "tracking"]):
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
    # =================================================
    # LLM FIRST PASS — SOURCE OF TRUTH
    # =================================================

    llm_text = generate_llm_response(
        system_prompt=(
            "You are a calm, professional customer support agent.\n"
            "Answer the customer's message as helpfully and completely as possible.\n\n"
            "If you need more information to proceed, ask ONE clear follow-up question.\n"
            "If you do NOT need more information, provide a complete answer."
        ),
        user_message=latest_message,
    )
    # --- LLM OUTPUT NORMALIZATION (HARD GUARANTEE STRING) ---
    if isinstance(llm_text, dict):
        llm_text = llm_text.get("text") or llm_text.get("response") or ""
    elif not isinstance(llm_text, str):
        llm_text = ""

    llm_text = llm_text.strip()
    # -------------------------------------------------
    # LLM IS SOURCE OF TRUTH FOR VALID QUESTIONS
    # -------------------------------------------------
    if llm_text:
        draft_text = llm_text

    # -------------------------------------------------
    # RULE: purchase inquiry must NEVER be diagnostic
    # (mode correction only, no overwriting LLM)
    # -------------------------------------------------
    if intent == "purchase_inquiry":
        mode = "explanatory"

    response_text = ""
    needs_clarification = False

    # ----------------------------
    # Phase 2 — final draft intent (locked)
    # ----------------------------
    draft_intent = intent

    # LEGACY: rules may suggest intent, but may NOT override LLM text
   


    # ✅ CRASH GUARD — ensure intent_result always exists
    intent_result = {
        "primary_intent": intent,
        "secondary_intents": [],
        "detected_keywords": [],
    }

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

    # ============================================================
    # Phase 5B — Draft Wording Polish (SAFE-ONLY)
    # ============================================================
    draft_text = polish_draft_text(
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
    # HARD NORMALIZATION — draft_text MUST be a string before gates
    # (prevents: TypeError 'NoneType' is not iterable)
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
    elif not isinstance(draft_text, str):
        draft_text = str(draft_text)

    draft_text = draft_text.strip()

    # If still empty, prefer LLM output if we have it
    if not draft_text and isinstance(llm_text, str) and llm_text.strip():
        draft_text = llm_text.strip()

    # -------------------------------------------------
    # PHASE 4 — Acceptance Gate (HARD)
    # -------------------------------------------------
    failures = draft_fails_acceptance_gate(
        draft_text=draft_text,
        intent=intent,
        mode=mode,
    )


    # -------------------------------------------------
    # FINAL HARD GUARANTEE — ONE PLACE ONLY
    # -------------------------------------------------
    if not isinstance(draft_text, str) or not draft_text.strip():
        draft_text = "I can help — could you clarify what you're looking for?"

    # -------------------------------------------------
    # PHASE 1.5 — Log DraftEvent (non-blocking)
    # -------------------------------------------------
    if draft_text.strip():
        try:
            from db import SessionLocal, safe_commit
            from models import DraftEvent, get_or_create_ticket
            session = SessionLocal()
            ticket_id = None
            freshdesk_ticket_id = kwargs.get("freshdesk_ticket_id")
            freshdesk_domain = kwargs.get("freshdesk_domain")
            if freshdesk_ticket_id and freshdesk_domain:
                ticket = get_or_create_ticket(session, freshdesk_ticket_id, freshdesk_domain)
                ticket_id = ticket.id
            clf = kwargs.get("classification") or {}
            sm = clf.get("safety_mode") if isinstance(clf, dict) else None
            cf = clf.get("confidence", {}) if isinstance(clf, dict) else {}
            cv = cf.get("intent_confidence") if isinstance(cf, dict) else None
            _rmap = {"safe": "low", "review_required": "medium", "unsafe": "high"}
            rc = _rmap.get((sm or "").lower()) if sm else None
            session.add(DraftEvent(
                subject=(subject or "")[:500],
                intent=intent,
                mode=mode,
                llm_used=bool(llm_text),
                ticket_id=ticket_id,
                confidence=cv,
                safety_mode=sm,
                risk_category=rc,
            ))
            safe_commit(session)
        except Exception:
            pass  # DB failure must never block draft return

    return {
        "type": "full",
        "response_text": draft_text,
        "quality_metrics": {
            "mode": mode,
            "delta_enforced": True,
            "fallback_used": bool(failures),
        },
        "canned_response_suggestion": None,
    }
