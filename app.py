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
from ai.strategy_engine import select_strategy, AUTO_TEMPLATE, PROACTIVE_DRAFT, ADVISORY_ONLY, SCAFFOLD
from ai.template_bridge import scanAndVerifyVariables, bridgeMetadataToTemplate, prepare_template_draft

from routes.sidecar_ui import sidecar_ui_bp
from routes.insights import insights_bp
from utils.build import build_id


# =========================
# App Initialization
# =========================

load_dotenv()

app = Flask(__name__)

# Register blueprints ONCE
app.register_blueprint(sidecar_ui_bp)
app.register_blueprint(insights_bp)

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
    # STEP 4: Strategy Selection (deterministic, no LLM)
    # ==========================================================
    ambiguity_detected = classification["confidence"].get("ambiguity_detected", False)

    strategy_result = select_strategy(
        intent=intent,
        confidence=confidence_overall,
        safety_mode=safety_mode,
        missing_info=missing_information,
        ambiguity_detected=ambiguity_detected,
    )

    selected_strategy = strategy_result["strategy"]

    # ==========================================================
    # STEP 5: Strategy-Conditional Draft Generation
    #
    # ONLY PROACTIVE_DRAFT calls generate_draft() (ChatGPT API).
    # All other strategies use local logic — no LLM invocation.
    # ==========================================================

    # Extracted data for template bridging + variable verification
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

    if selected_strategy == AUTO_TEMPLATE:
        # -------------------------------------------------------
        # AUTO_TEMPLATE: Load canned template, merge variables.
        # NO LLM call.
        # -------------------------------------------------------
        template_id = strategy_result.get("template_id")

        canned_responses = _load_canned_responses()
        template_result = prepare_template_draft(
            template_id=template_id,
            canned_responses=canned_responses,
            extracted_data=extracted_data,
        )

        draft_text = template_result["draft_text"]
        if not draft_text:
            # Template not found — degrade to scaffold
            draft_text = (
                "I can help with that.\n\n"
                "Let me look into this and get back to you shortly."
            )

        draft_result = {
            "type": "full",
            "response_text": draft_text,
            "quality_metrics": {
                "mode": "template",
                "delta_enforced": False,
                "fallback_used": not template_result["template_used"],
                "llm_invoked": False,
            },
            "canned_response_suggestion": None,
        }

    elif selected_strategy == PROACTIVE_DRAFT:
        # -------------------------------------------------------
        # PROACTIVE_DRAFT: Call generate_draft() (ChatGPT API).
        # This is the ONLY path that invokes the LLM.
        # -------------------------------------------------------
        agent_history = [
            m["text"]
            for m in conversation_history
            if isinstance(m, dict) and m.get("role") == "agent"
        ]
        last_ai_draft = agent_history[-1] if agent_history else None

        draft_output = generate_draft(
            latest_message=latest_message,
            intent=intent,
            prior_draft=last_ai_draft,
            prior_agent_messages=agent_history,
        )

        if isinstance(draft_output, dict):
            draft_result = draft_output
            draft_result.setdefault("quality_metrics", {})["llm_invoked"] = True
        else:
            draft_result = {
                "type": "full",
                "response_text": str(draft_output),
                "quality_metrics": {
                    "mode": "diagnostic",
                    "delta_enforced": True,
                    "fallback_used": False,
                    "llm_invoked": True,
                },
                "canned_response_suggestion": None,
            }

        draft_text = draft_result.get("response_text", "")

    elif selected_strategy == ADVISORY_ONLY:
        # -------------------------------------------------------
        # ADVISORY_ONLY: No sendable draft. Guidance only.
        # NO LLM call.
        # -------------------------------------------------------
        draft_text = (
            "[Advisory] This ticket requires manual agent review.\n\n"
            f"Detected intent: {intent}\n"
            f"Safety mode: {safety_mode}\n\n"
            "Please review the customer message and compose a response manually."
        )

        draft_result = {
            "type": "advisory",
            "response_text": draft_text,
            "quality_metrics": {
                "mode": "advisory",
                "delta_enforced": False,
                "fallback_used": False,
                "llm_invoked": False,
            },
            "canned_response_suggestion": None,
        }

    else:
        # -------------------------------------------------------
        # SCAFFOLD (default): Skeleton for agent to complete.
        # NO LLM call.
        # -------------------------------------------------------
        draft_text = (
            "Hi,\n\n"
            "Thanks for reaching out. "
            "I'd like to help, but I need a bit more information to proceed.\n\n"
            "Could you provide:\n"
            "1) [specific detail needed]\n"
            "2) [additional context]\n\n"
            "Once I have that, I can assist further."
        )

        draft_result = {
            "type": "scaffold",
            "response_text": draft_text,
            "quality_metrics": {
                "mode": "scaffold",
                "delta_enforced": False,
                "fallback_used": False,
                "llm_invoked": False,
            },
            "canned_response_suggestion": None,
        }

    # ==========================================================
    # STEP 6: Customer Name Injection (all strategies)
    # ==========================================================
    draft_text = draft_result.get("response_text", "")

    customer_name = data.get("customer_name")
    if customer_name and customer_name not in draft_text:
        draft_text = f"{customer_name}, {draft_text}"
        draft_result["response_text"] = draft_text

    # ==========================================================
    # STEP 7: Variable Verification
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

    # ==========================================================
    # STEP 8: Auto-Send Evaluation
    # ==========================================================
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
    # STEP 9: Build Response (v1.1 schema, unchanged)
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
        "freshdesk": {
            "issue_type": issue_type,
            "product": metadata.get("product") or "other",
            "tags": tags,
        },
    }

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

@app.route("/debug-env")
def debug_env():
    return {
        "domain": os.environ.get("FRESHDESK_DOMAIN"),
        "api_key_exists": bool(os.environ.get("FRESHDESK_API_KEY"))
    }

if __name__ == "__main__":
    app.run(debug=True, port=5000)
