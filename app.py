"""
FutureHub AI Sidecar (v1.0)
POST /api/v1/draft endpoint with intent classification and draft generation
"""

from flask import Flask, request, jsonify
from datetime import datetime
import time
import logging
import os
import subprocess

def deploy_info():
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        sha = "unknown"
    print(f"🚀 DEPLOY SHA: {sha}")
    print(f"🐍 PYTHON: {os.sys.version}")

deploy_info()

from dotenv import load_dotenv

from intent_classifier import detect_intent
from ai.draft_generator import generate_draft
from routes.sidecar_ui import sidecar_ui_bp
from ai.intent_normalization import normalize_intent
from ai.missing_info_detector import detect_missing_information
from ai.auto_send_evaluator import evaluate_auto_send
from utils.build import build_id
from ai.explanations import build_decision_explanation


load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.register_blueprint(sidecar_ui_bp)
# Near other blueprint registrations:

from routes.insights import insights_bp
app.register_blueprint(insights_bp)

# --------------------------------------------------
# Build metadata
# --------------------------------------------------
APP_BUILD = os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("GITHUB_SHA") or "unknown"
APP_BUILD_TIME = os.getenv("APP_BUILD_TIME") or datetime.utcnow().isoformat() + "Z"

# --------------------------------------------------
# Health check
# --------------------------------------------------
@app.route("/", methods=["GET", "HEAD"], endpoint="railway_root", provide_automatic_options=False)
def railway_root():
    return "OK", 200

# --------------------------------------------------
# Helpers
# --------------------------------------------------
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


# ==================================================
# API — DRAFT GENERATION
# ==================================================
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
    metadata = data.get("metadata") or {}

    if not subject or not latest_message:
        return error_response("invalid_input", "subject and latest_message are required")

    # --------------------------------------------------
    # Intent classification
    # --------------------------------------------------
    classification = detect_intent(
        latest_message,
        subject,
        metadata={
            "order_number": metadata.get("order_number"),
            "product": metadata.get("product"),
            "attachments": metadata.get("attachments") or [],
        },
    )

    combined = f"{subject} {latest_message}".lower()

    # Shipping override
    if any(k in combined for k in ["shipping", "order", "tracking", "where is my"]):
        classification["primary_intent"] = "shipping_status"
        classification["confidence"]["intent_confidence"] = 0.90
        classification["confidence"]["ambiguity_detected"] = False

    # Firmware override ✅
    elif any(k in combined for k in ["firmware", "update", "flash", "version"]):
        classification["primary_intent"] = "firmware_update_info"
        classification["confidence"]["intent_confidence"] = 0.85
        classification["confidence"]["ambiguity_detected"] = False


    normalized = normalize_intent(
        primary=classification["primary_intent"],
        secondary=classification.get("secondary_intent"),
    )

    intent = normalized["normalized_intent"]
    issue_type = normalized["issue_type"]
    tags = normalized["tags"]

    # --------------------------------------------------
    # Draft generation
    # --------------------------------------------------
    draft_result = generate_draft(
        latest_message=latest_message,
        intent=intent,
        prior_draft=None,
        prior_agent_messages=[],
    )

    if not isinstance(draft_result, dict):
        draft_result = {
            "type": "full",
            "response_text": str(draft_result),
        }

    # --------------------------------------------------
    # HARD UI NORMALIZATION (FINAL — DO NOT REMOVE)
    # response_text MUST be a STRING for JS
    # --------------------------------------------------
    rt = draft_result.get("response_text")

    if isinstance(rt, dict):
        rt = rt.get("text", "")
    elif rt is None:
        rt = ""
    else:
        rt = str(rt)

    rt = rt.strip()

    if not rt:
        rt = "I can help with that. Could you provide a bit more detail?"

    draft_result["response_text"] = rt

    # --------------------------------------------------
    # Auto-send evaluation
    # --------------------------------------------------
    confidence_overall = classification["confidence"]["intent_confidence"]

    missing_information = detect_missing_information(
        messages=[latest_message],
        intent={
            "primary": classification["primary_intent"],
            "confidence": confidence_overall,
        },
        mode="diagnostic",
        metadata=metadata,
    )

    auto_send_result = evaluate_auto_send(
        message=latest_message,
        intent=intent,
        intent_confidence=confidence_overall,
        safety_mode=classification.get("safety_mode") or "review_required",
        draft_text=rt,
        acceptance_failures=[],
        missing_information=missing_information,
    )

    processing_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))
    # -------------------------------
    # Decision Explanation (SAFE)
    # -------------------------------

    decision_explanation = build_decision_explanation(
        intent_data={
            "primary_intent": (
                draft_result
                .get("intent_classification", {})
                .get("primary_intent")
            ),
            "secondary_intents": (
                draft_result
                .get("intent_classification", {})
                .get("secondary_intents", [])
            ),
            "keywords": [],
        },
        confidence_score=(
            draft_result
            .get("intent_classification", {})
            .get("confidence", {})
            .get("overall", 0.0)
        ),
        auto_send_decision=(
            draft_result
            .get("auto_send", False)
        ),
        safety_mode=(
            draft_result
            .get("intent_classification", {})
            .get("safety_mode", "acceptable")
        ),
        missing_info=False,
    )

    draft_result["decision_explanation"] = decision_explanation


    # --------------------------------------------------
    # FINAL RESPONSE (SINGLE EXIT)
    # --------------------------------------------------
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
        },
        "draft": {
            "type": "full",
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
    response["decision_explanation"] = decision_explanation


    return jsonify(response), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
