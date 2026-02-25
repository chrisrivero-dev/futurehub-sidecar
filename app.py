"""
FutureHub AI Sidecar (v1.0)
POST /api/v1/draft endpoint with intent classification and draft generation
"""

from flask import Flask, request, jsonify
from datetime import datetime
import logging
import os
import time
import requests
from dotenv import load_dotenv

from intent_classifier import detect_intent
from ai.draft_generator import generate_draft
from ai.intent_normalization import normalize_intent
from ai.missing_info_detector import detect_missing_information
from ai.auto_send_evaluator import evaluate_auto_send
from ai.strategy_engine import select_strategy
from ai.template_bridge import scanAndVerifyVariables, bridgeMetadataToTemplate, prepare_template_draft

from routes.sidecar_ui import sidecar_ui_bp
from routes.insights import insights_bp
from routes.api_v1_analytics import analytics_bp
from utils.build import build_id

from audit import set_trace_id, get_trace_id
from audit.events import emit_event


# =========================
# App Initialization
# =========================

load_dotenv()

app = Flask(__name__)

# Register blueprints ONCE
app.register_blueprint(sidecar_ui_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(analytics_bp)

logger = logging.getLogger(__name__)


# =========================
# Build Metadata
# =========================

APP_BUILD = os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("GITHUB_SHA") or "unknown"
APP_BUILD_TIME = os.getenv("APP_BUILD_TIME") or datetime.utcnow().isoformat() + "Z"

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")


# =========================
# Global CORS (Single Source)
# =========================

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


# =========================
# Ticket Ingest Endpoint
# =========================
@app.route("/debug-env", endpoint="debug_env_unique")
def debug_env():

    return {
        "domain": os.environ.get("FRESHDESK_DOMAIN"),
        "api_key_exists": bool(os.environ.get("FRESHDESK_API_KEY"))
    }


@app.route("/ingest-ticket", methods=["POST", "OPTIONS"])
def ingest_ticket():

    # Handle preflight
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    # 🔥 Read environment variables at request time
    FRESHDESK_DOMAIN = os.environ.get("FRESHDESK_DOMAIN")
    FRESHDESK_API_KEY = os.environ.get("FRESHDESK_API_KEY")

    if not FRESHDESK_DOMAIN or not FRESHDESK_API_KEY:
        return jsonify({
            "error": "Freshdesk environment variables not configured",
            "domain_present": bool(FRESHDESK_DOMAIN),
            "api_key_present": bool(FRESHDESK_API_KEY)
        }), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    ticket_id = data.get("ticket_id")
    if not ticket_id:
        return jsonify({"error": "Missing ticket_id"}), 400

    auth = (FRESHDESK_API_KEY, "X")

    ticket_res = requests.get(
        f"https://{FRESHDESK_DOMAIN}/api/v2/tickets/{ticket_id}",
        auth=auth
    )

    if ticket_res.status_code != 200:
        return jsonify({
            "error": "Ticket fetch failed",
            "status": ticket_res.status_code,
            "details": ticket_res.text
        }), 500

    return jsonify(ticket_res.json()), 200


# -----------------------------------
# LLM kill switch
# -----------------------------------
def llm_allowed():
    return os.getenv("LLM_ENABLED", "false").lower() == "true"



@app.route("/", methods=["GET", "HEAD"], endpoint="railway_root", provide_automatic_options=False)
def railway_root():
    return "OK", 200


# Payload limits
MAX_SUBJECT_LENGTH = 500
MAX_MESSAGE_LENGTH = 10000
MAX_CONVERSATION_HISTORY = 50
MAX_CUSTOMER_NAME_LENGTH = 100
MAX_ATTACHMENTS = 10
MAX_PAYLOAD_BYTES = 1048576


def error_response(code, message, status=400, details=None):
    payload = {"success": False, "error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status


def get_confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.70:
        return "medium"
    if confidence >= 0.50:
        return "low"
    return "very_low"

@app.route("/api/v1/draft", methods=["POST"])
def draft():
    start_time = time.perf_counter()
    trace_id = set_trace_id()

    try:
        data = request.get_json() or {}
    except Exception:
        return error_response("malformed_json", "Request body must be valid JSON")

    subject = str(data.get("subject") or "").strip()
    latest_message = str(data.get("latest_message") or "").strip()
    conversation_history = data.get("conversation_history") or []

    if not subject or not latest_message:
        return error_response("invalid_input", "subject and latest_message are required")

    metadata = data.get("metadata") or {}
    attachments = metadata.get("attachments") or []

    # ── Audit: ticket_ingested ──
    try:
        emit_event("ticket_ingested", {
            "subject": subject[:200],
            "message_length": len(latest_message),
            "has_history": bool(conversation_history),
        })
    except Exception:
        pass

    # ==========================================================
    # STEP 1: Intent Classification (deterministic, no LLM)
    # ==========================================================
    classification = detect_intent(
        subject,
        latest_message,
        metadata={
            "order_number": metadata.get("order_number"),
            "product": metadata.get("product"),
            "attachments": attachments,
        },
    )

    # Shipping override — ONLY if classifier was uncertain
    combined = f"{subject} {latest_message}".lower()
    if (
        classification["primary_intent"] == "unknown_vague"
        and any(k in combined for k in ["shipping", "tracking", "where is my"])
    ):
        classification["primary_intent"] = "shipping_status"
        classification["confidence"]["intent_confidence"] = 0.90
        classification["confidence"]["ambiguity_detected"] = False

    # ==========================================================
    # STEP 2: Normalize Intent (deterministic, no LLM)
    # ==========================================================
    normalized = normalize_intent(
        primary=classification["primary_intent"],
        secondary=classification.get("secondary_intent"),
    )

    intent = normalized["normalized_intent"]
    issue_type = normalized["issue_type"]
    tags = normalized["tags"]

    confidence_overall = classification["confidence"]["intent_confidence"]

    # ── Audit: ai_analyze ──
    try:
        emit_event("ai_analyze", {
            "intent": intent,
            "confidence": confidence_overall,
            "ambiguity": classification["confidence"].get("ambiguity_detected", False),
            "safety_mode": classification.get("safety_mode"),
        })
    except Exception:
        pass

    # ==========================================================
    # STEP 3: Missing Information Detection (deterministic, no LLM)
    # ==========================================================
    last_customer_messages = [
        m["text"]
        for m in conversation_history
        if isinstance(m, dict) and m.get("role") == "customer"
    ][-2:]

    missing_information = detect_missing_information(
        messages=last_customer_messages,
        intent={
            "primary": classification["primary_intent"],
            "confidence": confidence_overall,
        },
        mode="diagnostic",
        metadata=metadata,
    )

    # Safety mode — guaranteed definition
    safety_mode = classification.get("safety_mode")
    if not safety_mode:
        if intent in ("shipping_status", "shipping_eta", "firmware_update_info"):
            safety_mode = "safe"
        else:
            safety_mode = "review_required"

    # ==========================================================
    # STEP 4: Strategy Selection (metadata/advisory tag only —
    #         does NOT gate LLM execution)
    # ==========================================================
    ambiguity_detected = classification["confidence"].get("ambiguity_detected", False)

    strategy_result = select_strategy(
        intent=intent,
        confidence=confidence_overall,
        safety_mode=safety_mode,
        missing_info=missing_information,
        ambiguity_detected=ambiguity_detected,
    )

    # ==========================================================
    # STEP 5: Retrieve matching templates (keyword/intent match)
    # ==========================================================
    extracted_data = {
        "customer_name": data.get("customer_name"),
        "order_number": metadata.get("order_number"),
        "product": metadata.get("product"),
        "device_model": metadata.get("product"),
        "tracking_number": metadata.get("tracking_number"),
        "firmware_version": metadata.get("firmware_version"),
        "email": metadata.get("email"),
    }
    extracted_data = {k: v for k, v in extracted_data.items() if v is not None}

    canned_responses = _load_canned_responses()
    matched_templates = _match_templates(intent, latest_message, canned_responses)

    # ==========================================================
    # STEP 6: Build augmented message for LLM (ALWAYS runs)
    #
    # Uses strictly-delimited prompt construction:
    #   - CUSTOMER MESSAGE appears first as authoritative source
    #   - Templates provided as reference guidance only
    #   - Final instruction ensures all questions are addressed
    # ==========================================================
    template_candidates = matched_templates
    augmented_input = prepare_augmented_message(latest_message, template_candidates)

    agent_history = [
        m["text"]
        for m in conversation_history
        if isinstance(m, dict) and m.get("role") == "agent"
    ]

    draft_output = generate_draft(
        latest_message=augmented_input,
        intent=intent,
        prior_draft=agent_history[-1] if agent_history else None,
        prior_agent_messages=agent_history,
    )

    if isinstance(draft_output, dict):
        draft_result = draft_output
    else:
        draft_result = {
            "type": "full",
            "response_text": str(draft_output),
            "quality_metrics": {
                "mode": "diagnostic",
                "delta_enforced": True,
                "fallback_used": False,
            },
            "canned_response_suggestion": None,
        }

    # Always mark LLM as invoked
    draft_result.setdefault("quality_metrics", {})["llm_invoked"] = True

    # ── Audit: draft_generated ──
    try:
        emit_event("draft_generated", {
            "intent": intent,
            "draft_type": draft_result.get("type"),
            "draft_length": len(draft_result.get("response_text", "")),
            "template_count": len(template_candidates),
            "last_2_customer_messages": last_customer_messages[-2:],
        })
    except Exception:
        pass

    # ==========================================================
    # STEP 7: Detect which template was materially used
    #         (informational only — does NOT gate any logic)
    # ==========================================================
    template_usage_guess = _detect_used_template(
        draft_text=draft_result.get("response_text", ""),
        matched_templates=template_candidates,
    )

    # Override strategy template_id with actual detected usage
    strategy_result["template_id"] = template_usage_guess

    # ==========================================================
    # STEP 8: Customer Name Injection
    # ==========================================================
    draft_text = draft_result.get("response_text", "")

    customer_name = data.get("customer_name")
    if customer_name and customer_name not in draft_text:
        draft_text = f"{customer_name}, {draft_text}"
        draft_result["response_text"] = draft_text

    # ==========================================================
    # STEP 9: Variable Verification
    # ==========================================================
    variable_verification = scanAndVerifyVariables(draft_text, extracted_data)

    # Merge blocking missing-info items into verification
    for item in missing_information.get("items", []):
        key = item.get("key", "")
        severity = item.get("severity", "non_blocking")
        already_in = any(m["key"] == key for m in variable_verification["missing"])
        if not already_in and severity == "blocking":
            variable_verification["missing"].append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "required": True,
            })
            variable_verification["all_satisfied"] = False
            variable_verification["has_required_missing"] = True

    # ── Audit: delta_validation_result ──
    try:
        emit_event("delta_validation_result", {
            "all_satisfied": variable_verification["all_satisfied"],
            "missing_count": len(variable_verification["missing"]),
            "has_required_missing": variable_verification.get("has_required_missing", False),
            "validation_passed": variable_verification["all_satisfied"],
        })
    except Exception:
        pass

    # ==========================================================
    # STEP 10: Auto-Send Evaluation
    # ==========================================================
    # Inject ambiguity and variable flags so auto-send gating can check them
    missing_information["ambiguity_detected"] = ambiguity_detected
    missing_information["has_required_missing"] = variable_verification.get("has_required_missing", False)

    auto_send_result = evaluate_auto_send(
        message=latest_message,
        intent=intent,
        intent_confidence=confidence_overall,
        safety_mode=safety_mode,
        draft_text=draft_result,
        acceptance_failures=draft_result.get("quality_metrics", {}).get("acceptance_failures", []),
        missing_information=missing_information,
    )

    # ==========================================================
    # STEP 11: Build Response (v1.1 schema, unchanged)
    # ==========================================================
    processing_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))

    response = {
        "success": True,
        "version": "1.1",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "processing_time_ms": processing_time_ms,
        "intent_classification": {
            "primary_intent": classification["primary_intent"],
            "confidence": {
                "overall": confidence_overall,
                "label": get_confidence_label(confidence_overall),
                "ambiguity_detected": classification["confidence"]["ambiguity_detected"],
            },
            "safety_mode": classification.get("safety_mode"),
        },
        "strategy": {
            "selected": strategy_result["strategy"],
            "reason": strategy_result["reason"],
            "template_id": strategy_result.get("template_id"),
        },
        "draft": {
            "type": draft_result["type"],
            "response_text": draft_result["response_text"],
        },
        "variable_verification": {
            "all_satisfied": variable_verification["all_satisfied"],
            "missing": variable_verification["missing"],
            "satisfied": variable_verification["satisfied"],
            "has_required_missing": variable_verification.get("has_required_missing", False),
        },
        "auto_send": bool(auto_send_result.get("auto_send")),
        "auto_send_reason": auto_send_result.get("auto_send_reason"),
        "agent_guidance": {
            "auto_send_eligible": bool(auto_send_result.get("auto_send")),
            "requires_review": not bool(auto_send_result.get("auto_send")),
            "reason": auto_send_result.get("auto_send_reason"),
        },
        "template_suggestions": [
            {"id": t["id"], "title": t["title"]}
            for t in template_candidates
        ],
        "template_usage_guess": template_usage_guess,
        "freshdesk": {
            "issue_type": issue_type,
            "product": metadata.get("product") or "other",
            "tags": tags,
        },
    }

    # ==========================================================
    # STEP 12: Governance evaluation + memory logging (non-blocking)
    # ==========================================================
    try:
        from services.memory_service import log_ticket_memory
        from governance.evaluator import evaluate_send_readiness

        from governance.evaluator import _risk_category
        risk_level = _risk_category(safety_mode)

        gov = evaluate_send_readiness(
            intent=intent,
            confidence=confidence_overall,
            risk_level=risk_level,
            safety_mode=safety_mode,
            sensitive_flag=False,
            ambiguity_detected=ambiguity_detected,
            has_required_missing=variable_verification.get("has_required_missing", False),
            delta_passed=variable_verification["all_satisfied"],
        )

        # auto_sent is False in stub mode (human remains final authority)
        auto_sent = False

        log_ticket_memory({
            "subject": subject,
            "latest_message": latest_message[:500],
            "primary_intent": intent,
            "confidence": confidence_overall,
            "safety_mode": safety_mode,
            "strategy": strategy_result.get("strategy"),
            "auto_send": auto_send_result.get("auto_send", False),
            "auto_send_reason": auto_send_result.get("auto_send_reason"),
            "draft_outcome": "follow-up expected" if not auto_send_result.get("auto_send") else "resolved",
            "template_id": strategy_result.get("template_id"),
            "ambiguity": ambiguity_detected,
            "processing_ms": processing_time_ms,
            "auto_sent": auto_sent,
            "human_edited": False,
            "edit_diff_length": 0,
            "customer_followup": False,
            "ticket_reopened": False,
            "risk_category": gov["risk_category"],
            "confidence_bucket": gov["confidence_bucket"],
        })

        response["governance"] = {
            "auto_send_allowed": gov["auto_send_allowed"],
            "reasons": gov["reasons"],
            "risk_category": gov["risk_category"],
            "confidence_bucket": gov["confidence_bucket"],
        }
        response["trace_id"] = trace_id
    except Exception:
        pass  # non-blocking — never fail the draft response

    return jsonify(response), 200


# ==========================================================
# Canned Responses Loader (file-cached)
# ==========================================================
import json as _json

_CANNED_RESPONSES_CACHE = None

def _load_canned_responses():
    global _CANNED_RESPONSES_CACHE
    if _CANNED_RESPONSES_CACHE is not None:
        return _CANNED_RESPONSES_CACHE

    canned_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "static", "data", "canned_responses.json",
    )
    try:
        with open(canned_path, "r", encoding="utf-8") as f:
            _CANNED_RESPONSES_CACHE = _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        _CANNED_RESPONSES_CACHE = []

    return _CANNED_RESPONSES_CACHE


# ==========================================================
# Template Matching — intent + keyword (no vector DB)
# ==========================================================
from ai.strategy_engine import TEMPLATE_INTENT_MAP

def _match_templates(intent, message, canned_responses):
    """
    Return top matching templates as list of {id, title, content}.
    Uses intent map first, then keyword fallback.
    Max 2 templates returned.
    """
    if not canned_responses:
        return []

    by_id = {str(t.get("id")): t for t in canned_responses}
    matched = []
    seen_ids = set()

    # 1) Primary: intent-mapped template
    primary_id = TEMPLATE_INTENT_MAP.get(intent)
    if primary_id and primary_id in by_id:
        t = by_id[primary_id]
        matched.append({
            "id": str(t["id"]),
            "title": t.get("title", ""),
            "content": t.get("content", ""),
        })
        seen_ids.add(primary_id)

    # 2) Secondary: keyword scan across all templates
    msg_lower = message.lower()
    for t in canned_responses:
        tid = str(t.get("id", ""))
        if tid in seen_ids:
            continue

        title = (t.get("title") or "").lower()
        content = (t.get("content") or "").lower()

        # Check if significant words from the message appear in template
        title_words = set(title.split())
        # Match if >=2 title words appear in message, or title substring match
        overlap = sum(1 for w in title_words if len(w) > 3 and w in msg_lower)
        if overlap >= 2 or title in msg_lower:
            matched.append({
                "id": tid,
                "title": t.get("title", ""),
                "content": t.get("content", ""),
            })
            seen_ids.add(tid)

        if len(matched) >= 2:
            break

    return matched


# ==========================================================
# Augmented Message Builder
# ==========================================================

def prepare_augmented_message(latest_message, matched_templates):
    """
    Constructs a strictly-delimited augmented prompt.
    Prevents instruction pollution.
    CUSTOMER MESSAGE always appears first as the authoritative source.
    """
    prompt = "=== CUSTOMER MESSAGE (AUTHORITATIVE SOURCE) ===\n"
    prompt += f"{latest_message}\n\n"

    if matched_templates:
        prompt += "=== TEMPLATE REFERENCES (FOR GUIDANCE, DO NOT COPY VERBATIM) ===\n"
        for idx, temp in enumerate(matched_templates, 1):
            prompt += f"[Reference {idx}: {temp['title']} (ID: {temp['id']})]\n"
            prompt += f"{temp['content']}\n\n"

    prompt += "=== FINAL INSTRUCTION ===\n"
    prompt += (
        "Identify and answer ALL explicit and implicit questions in the CUSTOMER MESSAGE.\n"
        "Use TEMPLATE REFERENCES only to ensure policy accuracy.\n"
        "Do not copy template text verbatim.\n"
        "If the message contains bespoke details not covered by templates, use reasoning.\n"
        "Do not skip secondary questions.\n"
    )

    return prompt


# ==========================================================
# Template Usage Detection (post-LLM)
# ==========================================================

def _detect_used_template(draft_text, matched_templates):
    """
    After the LLM generates a draft, detect which template (if any)
    was materially used by checking phrase overlap.
    Returns template_id or None.
    """
    if not draft_text or not matched_templates:
        return None

    draft_lower = draft_text.lower()
    best_id = None
    best_score = 0

    for t in matched_templates:
        content = (t.get("content") or "").lower()
        if not content:
            continue

        # Split into meaningful phrases (sentences / fragments)
        phrases = [p.strip() for p in content.replace("\n", ". ").split(". ") if len(p.strip()) > 15]
        if not phrases:
            continue

        hits = sum(1 for p in phrases if p in draft_lower)
        score = hits / len(phrases) if phrases else 0

        if score > best_score and score >= 0.3:
            best_score = score
            best_id = t.get("id")

    return best_id

@app.route("/debug-env")
def debug_env():
    return {
        "domain": os.environ.get("FRESHDESK_DOMAIN"),
        "api_key_exists": bool(os.environ.get("FRESHDESK_API_KEY"))
    }


# ==========================================================
# Freshdesk Lifecycle Webhook
# POST /api/v1/webhooks/freshdesk
# ==========================================================

@app.route("/api/v1/webhooks/freshdesk", methods=["POST"])
def freshdesk_webhook():
    from sqlalchemy.exc import IntegrityError
    from db import SessionLocal
    from models import TicketReply, TicketStatusChange

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "missing JSON body"}), 400

    event_type      = data.get("event_type")
    fd_ticket_id    = data.get("ticket_id")
    status          = data.get("status")
    conversation_id = data.get("conversation_id")
    author_id       = data.get("author_id")

    try:
        created_at_raw = data.get("created_at")
        utc_now = (
            datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            if created_at_raw
            else datetime.utcnow()
        )
    except (ValueError, AttributeError):
        utc_now = datetime.utcnow()

    print(">>> WEBHOOK RECEIVED:", event_type)

    session = SessionLocal()
    try:
        if event_type == "ticket_closed":
            session.add(TicketStatusChange(
                ticket_id=fd_ticket_id,
                old_status="unknown",
                new_status="closed",
                freshdesk_updated_at=utc_now,
            ))

        elif event_type == "ticket_updated" and status:
            session.add(TicketStatusChange(
                ticket_id=fd_ticket_id,
                old_status="unknown",
                new_status=status,
                freshdesk_updated_at=utc_now,
            ))

        elif event_type == "conversation_created":
            session.add(TicketReply(
                ticket_id=fd_ticket_id,
                draft_event_id=None,
                direction="inbound",
                freshdesk_conversation_id=conversation_id,
                body_hash=None,
                body_length=None,
                edited=None,
            ))

        session.commit()
        print(">>> EVENT COMMITTED")
        return jsonify({"success": True, "event_logged": event_type}), 200

    except IntegrityError:
        session.rollback()
        print(">>> DUPLICATE EVENT, SKIPPED:", event_type)
        return jsonify({"success": True, "event_logged": event_type, "duplicate": True}), 200

    except Exception as e:
        session.rollback()
        logger.error("Webhook DB failure: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        session.close()



# ==========================================================
# Ticket Review Endpoint
# GET /api/v1/tickets/<ticket_id>/review
# ==========================================================

@app.route("/api/v1/tickets/<int:ticket_id>/review", methods=["GET"])
def ticket_review(ticket_id):
    from db import SessionLocal
    from models import Ticket, DraftEvent, TicketReply, TicketStatusChange

    empty = {
        "success": True,
        "ticket_id": ticket_id,
        "draft_summary": {
            "intent": None,
            "confidence": None,
            "risk_category": None,
            "strategy": None,
            "llm_used": False,
            "edited": False,
        },
        "lifecycle": {
            "outbound_count": 0,
            "inbound_count": 0,
            "edited_count": 0,
            "followup_detected": False,
            "reopened": False,
        },
        "kb_recommendations": [],
    }

    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter_by(freshdesk_ticket_id=ticket_id).first()
        if not ticket:
            return jsonify(empty), 200

        local_id = ticket.id

        # ── Fetch all related rows ──────────────────────────────
        drafts = (
            session.query(DraftEvent)
            .filter(DraftEvent.ticket_id == local_id)
            .order_by(DraftEvent.created_at.desc())
            .all()
        )

        replies = (
            session.query(TicketReply)
            .filter(TicketReply.ticket_id == local_id)
            .order_by(TicketReply.created_at.asc())
            .all()
        )

        status_changes = (
            session.query(TicketStatusChange)
            .filter(TicketStatusChange.ticket_id == local_id)
            .all()
        )

        # ── Draft Summary (most recent DraftEvent) ─────────────
        latest = drafts[0] if drafts else None

        # ── Reply counts ────────────────────────────────────────
        outbound = [r for r in replies if r.direction == "outbound"]
        inbound  = [r for r in replies if r.direction == "inbound"]
        edited_outbound = [r for r in outbound if r.edited is True]
        edited_count = len(edited_outbound)
        edited_flag = edited_count > 0

        # strategy = DraftEvent.mode (e.g. "template", "llm", "hybrid")
        strategy = latest.mode if latest else None

        # ── Followup detected ───────────────────────────────────
        # True if >1 inbound replies arrived after the first outbound reply
        followup_detected = False
        if outbound and inbound:
            first_outbound_at = outbound[0].created_at
            inbound_after = [r for r in inbound if r.created_at > first_outbound_at]
            followup_detected = len(inbound_after) > 1

        # ── Reopened ────────────────────────────────────────────
        # True if any status transition went from resolved/closed → open
        reopened = any(
            s.old_status in ("resolved", "closed") and s.new_status == "open"
            for s in status_changes
        )

        # ── Risk Category (lifecycle-computed) ──────────────────
        # high: edited_count > 1, or reopened, or confidence < 0.75
        # medium: edited_count == 1
        # low: otherwise
        confidence_val = latest.confidence if latest else None
        if edited_count > 1 or reopened or (confidence_val is not None and confidence_val < 0.75):
            risk_category = "high"
        elif edited_count == 1:
            risk_category = "medium"
        else:
            risk_category = "low"

        return jsonify({
            "success": True,
            "ticket_id": ticket_id,
            "draft_summary": {
                "intent": latest.intent if latest else None,
                "confidence": confidence_val,
                "risk_category": risk_category,
                "strategy": strategy,
                "llm_used": latest.llm_used if latest else False,
                "edited": edited_flag,
            },
            "lifecycle": {
                "outbound_count": len(outbound),
                "inbound_count": len(inbound),
                "edited_count": edited_count,
                "followup_detected": followup_detected,
                "reopened": reopened,
            },
            "kb_recommendations": [],
        }), 200

    except Exception as e:
        logger.error("Ticket review query failed: %s", e)
        return jsonify(empty), 200

    finally:
        session.close()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
