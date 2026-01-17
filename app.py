"""
FutureHub AI Sidecar (v1.0)
POST /api/v1/draft endpoint with intent classification and draft generation
"""

from flask import Flask, request, jsonify
from datetime import datetime
import time

from intent_classifier import detect_intent
from ai.draft_generator import generate_draft
from flask import redirect
from routes.sidecar_ui import sidecar_ui_bp


app = Flask(__name__)

# Payload size limits (v1.0 contract)
MAX_SUBJECT_LENGTH = 500
MAX_MESSAGE_LENGTH = 10000
MAX_CONVERSATION_HISTORY = 50
MAX_CUSTOMER_NAME_LENGTH = 100
MAX_ATTACHMENTS = 10
MAX_PAYLOAD_BYTES = 1048576  # 1MB


@app.route("/api/v1/draft", methods=["POST"])
def draft():
    """
    Generate draft response for support ticket.
    Conforms to v1.0 API contract.
    """
    start_time = time.perf_counter()

    # ----------------------------
    # Parse JSON
    # ----------------------------
    try:
        data = request.get_json()
    except Exception:
        return error_response(
            code="malformed_json",
            message="Request body must be valid JSON",
            status=400,
        )
    # 🔥 HARD CONTRACT ENFORCEMENT
    if "message" in data:
        return error_response(
            code="invalid_input",
            message="Field 'message' is not supported. Use 'latest_message' only.",
            details={"invalid_field": "message"},
            status=400,
        )

    if not data:
        return error_response(
            code="malformed_json",
            message="Request body must be valid JSON",
            status=400,
        )

    # ----------------------------
    # Payload size
    # ----------------------------
    if request.content_length and request.content_length > MAX_PAYLOAD_BYTES:
        return error_response(
            code="payload_too_large",
            message=f"Request exceeds maximum size of {MAX_PAYLOAD_BYTES} bytes",
            details={
                "request_size_bytes": request.content_length,
                "max_size_bytes": MAX_PAYLOAD_BYTES,
            },
            status=400,
        )

    # ----------------------------
    # Required fields
    # ----------------------------
    required_fields = ["subject", "latest_message", "conversation_history"]
    missing = []

    for field in required_fields:
        if field not in data or data[field] is None:
            missing.append(field)
        elif field == "conversation_history" and not isinstance(data[field], list):
            missing.append(field)

    if missing:
        return error_response(
            code="invalid_input",
            message=f"Missing or invalid required fields: {', '.join(missing)}",
            details={
                "missing_fields": missing,
                "required_fields": required_fields,
            },
            status=400,
        )

    # ----------------------------
    # Field length validation
    # ----------------------------
    if len(data["subject"]) > MAX_SUBJECT_LENGTH:
        return error_response(
            code="payload_too_large",
            message=f"Field 'subject' exceeds maximum length of {MAX_SUBJECT_LENGTH} characters",
            details={"field": "subject", "max_length": MAX_SUBJECT_LENGTH},
            status=400,
        )

    if len(data["latest_message"]) > MAX_MESSAGE_LENGTH:
        return error_response(
            code="payload_too_large",
            message=f"Field 'latest_message' exceeds maximum length of {MAX_MESSAGE_LENGTH} characters",
            details={"field": "latest_message", "max_length": MAX_MESSAGE_LENGTH},
            status=400,
        )

    # ----------------------------
    # Conversation history
    # ----------------------------
    conversation_history = data["conversation_history"]

    if len(conversation_history) > MAX_CONVERSATION_HISTORY:
        return error_response(
            code="payload_too_large",
            message=f"conversation_history exceeds maximum of {MAX_CONVERSATION_HISTORY} messages",
            details={
                "field": "conversation_history",
                "message_count": len(conversation_history),
                "max_messages": MAX_CONVERSATION_HISTORY,
            },
            status=400,
        )

    for i, msg in enumerate(conversation_history):
        if not isinstance(msg, dict):
            return error_response(
                code="invalid_input",
                message=f"Message at index {i} must be an object",
                details={"message_index": i},
                status=400,
            )

        if msg.get("role") not in ["customer", "agent"]:
            return error_response(
                code="invalid_input",
                message=f"Message at index {i} must have role 'customer' or 'agent'",
                details={"message_index": i},
                status=400,
            )

        if not isinstance(msg.get("text"), str):
            return error_response(
                code="invalid_input",
                message=f"Message at index {i} must contain text",
                details={"message_index": i},
                status=400,
            )

        if len(msg["text"]) > MAX_MESSAGE_LENGTH:
            return error_response(
                code="payload_too_large",
                message=f"Message text at index {i} exceeds maximum length",
                details={"message_index": i, "max_length": MAX_MESSAGE_LENGTH},
                status=400,
            )

    # ----------------------------
    # Optional fields
    # ----------------------------
    customer_name = data.get("customer_name")
    if customer_name and len(customer_name) > MAX_CUSTOMER_NAME_LENGTH:
        return error_response(
            code="payload_too_large",
            message="Field 'customer_name' exceeds maximum length",
            details={"field": "customer_name", "max_length": MAX_CUSTOMER_NAME_LENGTH},
            status=400,
        )

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    attachments = metadata.get("attachments", [])
    if not isinstance(attachments, list):
        attachments = []

    if len(attachments) > MAX_ATTACHMENTS:
        return error_response(
            code="payload_too_large",
            message=f"Attachments exceed maximum of {MAX_ATTACHMENTS}",
            details={"attachment_count": len(attachments), "max_attachments": MAX_ATTACHMENTS},
            status=400,
        )

    classification_metadata = {
        "order_number": metadata.get("order_number"),
        "product": metadata.get("product"),
        "attachments": attachments,
    }

    # ----------------------------
    # Intent
    # ----------------------------
    classification = detect_intent(
        subject=data["subject"],
        message=data["latest_message"],
        metadata=classification_metadata,
    )

    # ----------------------------
    # Context for draft generation
    # ----------------------------
    intent = classification["primary_intent"]
    latest_message = data["latest_message"]

    # Pull prior agent messages (including previous AI drafts)
    agent_history = [
        m["text"]
        for m in conversation_history
        if m.get("role") == "agent" and isinstance(m.get("text"), str)
    ]
    last_ai_draft = agent_history[-1] if agent_history else None

    # -------------------------------------------------
    # PHASE 1.1 LOCKED
    # Do NOT pass `mode` or legacy `message` here.
    # Draft behavior is derived inside generate_draft().
    # -------------------------------------------------
    # ----------------------------
    # Draft (AI generator) -> RETURNS STRING
    # ----------------------------
    draft_text = generate_draft(
        latest_message=latest_message,
        intent=intent,
        prior_draft=last_ai_draft,
        prior_agent_messages=agent_history,
    )



    # Normalize into the shape the rest of this file expects
    draft_result = {
        "type": "full",
        "response_text": draft_text,
        "quality_metrics": {},
    }
    canned_response_suggestion = draft_result.get("canned_response_suggestion")

    # ----------------------------
    # Timing
    # ----------------------------
    processing_time_ms = max(1, int((time.perf_counter() - start_time) * 1000))

    # Base confidence from classifier
    confidence_overall = classification["confidence"]["intent_confidence"]

    # v1 contract normalization
    if intent == "shipping_status" and classification_metadata.get("order_number"):
        confidence_overall = max(confidence_overall, 0.9)

    # CRITICAL: sync back into classification for auto-send logic
    classification["confidence"]["intent_confidence"] = confidence_overall

    # Now calculate auto-send
    auto_send_eligible = calculate_auto_send_eligible(
        classification=classification,
        draft_result=draft_result,
        attachments=attachments,
    )

    # ----------------------------
    # Response
    # ----------------------------
    response = {
        "success": True,
        "draft_available": True,
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "processing_time_ms": processing_time_ms,
        "intent_classification": {
            "primary_intent": classification["primary_intent"],
            "secondary_intents": classification["secondary_intents"],
            "confidence": {
                "overall": confidence_overall,
                "dimensions": {
                    "intent_confidence": confidence_overall,
                },
                "label": get_confidence_label(confidence_overall),
                "ambiguity_detected": classification["confidence"]["ambiguity_detected"],
            },
            "safety_mode": classification["safety_mode"],
            "tone_modifier": classification["tone_modifier"],
            "device_behavior_detected": classification["device_behavior_detected"],
            "attempted_actions": classification["attempted_actions"],
            "signal_breakdown": classification["scores"],
            "classification_reasoning": (
                f"Intent detected as {classification['primary_intent']} "
                "based on keyword analysis"
            ),
        },
        "draft": {
            "type": draft_result["type"],
            "response_text": draft_result["response_text"],
            "quality_metrics": draft_result["quality_metrics"],
        },
        "knowledge_retrieval": {
            "sources_consulted": [],
            "coverage": "none",
            "gaps": ["Knowledge retrieval not yet implemented"],
        },
        "agent_guidance": {
            "auto_send_eligible": auto_send_eligible,
            "requires_review": not auto_send_eligible,
            "reason": build_reason(classification, auto_send_eligible),
            "recommendation": build_recommendation(classification),
            "suggested_actions": build_suggested_actions(classification),
        },
    }

    if canned_response_suggestion:
        response["agent_guidance"]["canned_response_suggestion"] = canned_response_suggestion

    return jsonify(response), 200


def calculate_auto_send_eligible(classification, draft_result, attachments):
    """
    Calculate auto-send eligibility per v1.0 contract.

    Criteria (ALL must be true):
    1. Intent is shipping_status (ONLY)
    2. Confidence >= 0.85
    3. Draft type is "full"
    4. No attachments
    5. Safety mode is "safe"
    6. No ambiguity detected
    """
    intent = classification["primary_intent"]
    confidence = classification["confidence"]["intent_confidence"]
    safety_mode = classification["safety_mode"]
    ambiguity_detected = classification["confidence"]["ambiguity_detected"]
    draft_type = draft_result.get("type", "full")

    if intent != "shipping_status":
        return False
    if confidence < 0.85:
        return False
    if draft_type != "full":
        return False
    if attachments and len(attachments) > 0:
        return False
    if safety_mode != "safe":
        return False
    if ambiguity_detected:
        return False

    return True


def build_reason(classification, auto_send_eligible):
    """
    Human-readable explanation for agent guidance.
    Must satisfy v1.0 contract expectations.
    """
    intent = classification["primary_intent"]
    safety_mode = classification["safety_mode"]

    if auto_send_eligible:
        return (
            f"High-confidence {intent} request meets v1.0 auto-send criteria "
            "and does not require agent review."
        )

    if safety_mode == "unsafe":
        return (
            f"Diagnostic intent '{intent}' requires human review "
            "before any response is sent."
        )

    return (
        f"Intent '{intent}' does not meet auto-send criteria "
        "and requires agent review."
    )


def get_confidence_label(confidence):
    """Convert confidence score to label"""
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.70:
        return "medium"
    if confidence >= 0.50:
        return "low"
    return "very_low"


def build_recommendation(classification):
    """
    Provide agent-facing recommendation text.
    This function must not imply review when auto-send is allowed.
    """
    intent = classification.get("primary_intent", "unknown")
    if intent == "shipping_status":
        return "Response may be sent automatically."
    return "Agent review recommended before responding."


def build_suggested_actions(classification):
    """Build suggested actions list based on classification"""
    intent = classification["primary_intent"]

    actions_map = {
        "not_hashing": [
            "Request debug.log and getblockchaininfo output",
            "Review logs for error patterns",
            "Consider: Node Not Hashing Troubleshooting canned response",
        ],
        "sync_delay": [
            "Request getblockchaininfo output",
            "Check if blocks are incrementing",
            "Consider: Node Sync Troubleshooting canned response",
        ],
        "firmware_issue": [
            "Request firmware version and update logs",
            "Do NOT provide recovery steps",
            "Escalate to engineering if device bricked",
        ],
        "performance_issue": [
            "Request description of restart pattern",
            "Check temperature and fan status",
            "Request debug.log if persistent",
        ],
        "shipping_status": [
            "Look up order in admin system",
            "Provide accurate tracking information",
            "Set realistic delivery expectations",
        ],
        "setup_help": [
            "Provide step-by-step setup instructions",
            "Confirm device is brand new",
            "Reference setup documentation",
        ],
        "warranty_rma": [
            "Explain RMA process at high level",
            "Do NOT guarantee refund or replacement",
            "Check warranty coverage in system",
        ],
        "general_question": [
            "Provide educational explanation",
            "Use neutral, informative tone",
            "Reference documentation if available",
        ],
        "unknown_vague": [
            "Ask clarifying questions",
            "Use multiple-choice format if possible",
            "Be patient and helpful",
        ],
    }

    return actions_map.get(intent, ["Review customer message", "Provide appropriate response"])


def error_response(code, message, details=None, status=400):
    """Build standardized error response"""
    error_obj = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if details:
        error_obj["error"]["details"] = details

    return jsonify(error_obj), status


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return (
        jsonify(
            {
                "status": "healthy",
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ),
        200,
    )
@app.route("/", methods=["GET"])
def root():
    return redirect("/sidecar/")
app.register_blueprint(sidecar_ui_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
