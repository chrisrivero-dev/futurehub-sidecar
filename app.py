"""
FutureHub AI Sidecar (v1.0)
POST /api/v1/draft endpoint with intent classification and draft generation
"""

from flask import Flask, request, jsonify
from datetime import datetime
import time
import logging
import os

from intent_classifier import detect_intent
from ai.draft_generator import generate_draft
from routes.sidecar_ui import sidecar_ui_bp
from ai.intent_normalization import normalize_intent
from ai.missing_info_detector import detect_missing_information
from ai.auto_send_evaluator import evaluate_auto_send
from dotenv import load_dotenv
from utils.build import build_id
# Near other blueprint registrations:

from routes.insights import insights_bp

# ✅ Ensure app exists BEFORE registering blueprints
app = Flask(__name__)

# Existing blueprint registrations (keep yours here)
app.register_blueprint(sidecar_ui_bp)
app.register_blueprint(insights_bp)

load_dotenv()


logger = logging.getLogger(__name__)

import os
from datetime import datetime

APP_BUILD = os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("GITHUB_SHA") or "unknown"
APP_BUILD_TIME = os.getenv("APP_BUILD_TIME") or datetime.utcnow().isoformat() + "Z"





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
    autosend_confidence = 0.0

    try:
        data = request.get_json() or {}
    except Exception:
        return error_response("malformed_json", "Request body must be valid JSON")

    subject = str(data.get("subject") or "").strip()
    latest_message = str(data.get("latest_message") or "").strip()

    # 🔧 FIX: normalize payload for downstream code
    message = str(data.get("message") or "").strip() or latest_message

    conversation_history = data.get("conversation_history") or []

    if not subject or not latest_message:
        return error_response("invalid_input", "subject and latest_message are required")

    # --- everything else in your function continues here ---


    metadata = data.get("metadata") or {}
    attachments = metadata.get("attachments") or []

    classification = detect_intent(
         subject,
        latest_message,
        metadata={
            "order_number": metadata.get("order_number"),
            "product": metadata.get("product"),
            "attachments": attachments,
        },
    )

    # Shipping override
    combined = f"{subject} {latest_message}".lower()
    # Shipping override — ONLY if classifier was uncertain
    combined = f"{subject} {latest_message}".lower()

    if (
        classification["primary_intent"] == "unknown_vague"
        and any(k in combined for k in ["shipping", "tracking", "where is my"])
    ):
        classification["primary_intent"] = "shipping_status"
        classification["confidence"]["intent_confidence"] = 0.90
        classification["confidence"]["ambiguity_detected"] = False


    normalized = normalize_intent(
        primary=classification["primary_intent"],
        secondary=classification.get("secondary_intent"),
    )

    intent = normalized["normalized_intent"]
    issue_type = normalized["issue_type"]
    tags = normalized["tags"]

    agent_history = [
        m["text"]
        for m in conversation_history
        if isinstance(m, dict) and m.get("role") == "agent"
    ]
    last_ai_draft = agent_history[-1] if agent_history else None

    # ----------------------------
    # Draft generation
    # ----------------------------
    draft_output = generate_draft(
        latest_message=latest_message,
        intent=intent,
        prior_draft=last_ai_draft,
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

    draft_text = draft_result.get("response_text", "")

    customer_name = data.get("customer_name")
    if customer_name and customer_name not in draft_text:
        draft_text = f"{customer_name}, {draft_text}"
        draft_result["response_text"] = draft_text

    confidence_overall = classification["confidence"]["intent_confidence"]
    autosend_confidence = confidence_overall

    # Missing info detection
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
    # -------------------------------------------------
    # Safety mode — guaranteed definition
    # -------------------------------------------------
    safety_mode = classification.get("safety_mode")

    if not safety_mode:
        if intent in ("shipping_status", "shipping_eta", "firmware_update_info"):
            safety_mode = "safe"
        else:
            safety_mode = "review_required"


    # ----------------------------
    # Auto-send evaluation (FIXED SIGNATURE)
    # ----------------------------
    auto_send_result = evaluate_auto_send(
         message=latest_message,
        intent=intent,
        intent_confidence=autosend_confidence,
        safety_mode=safety_mode,
        draft_text=draft_result,
        acceptance_failures=draft_result.get("quality_metrics", {}).get("acceptance_failures", []),
        missing_information=missing_information,
    )


    processing_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))

    response = {
        "success": True,
        "version": "1.0",
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
        "draft": {
            "type": draft_result["type"],
            "response_text": draft_result["response_text"],
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
