# routes/ai_draft.py
"""
AI Draft Generation API
Sidecar service endpoint for draft generation
"""

from flask import Blueprint, request, jsonify
import time
import logging

from ai.draft_generator import generate_draft
from intent_classifier import detect_intent

logger = logging.getLogger(__name__)

# Create Blueprint
ai_draft_bp = Blueprint('ai_draft', __name__, url_prefix='/api/v1')

# Payload size limits (v1.0 contract)
MAX_SUBJECT_LENGTH = 500
MAX_MESSAGE_LENGTH = 10000
MAX_CONVERSATION_HISTORY = 50
MAX_CUSTOMER_NAME_LENGTH = 100
MAX_ATTACHMENTS = 10
MAX_PAYLOAD_BYTES = 1048576  # 1MB

@ai_draft_bp.route("/draft", methods=["POST"])
def draft():
    start_time = time.perf_counter()
    autosend_confidence = 0.0

    data = request.get_json() or {}

    subject = str(data.get("subject") or "").strip()
    latest_message = str(data.get("latest_message") or "").strip()
    conversation_history = data.get("conversation_history") or []

    if not subject or not latest_message:
        return jsonify({
            "draft_available": False,
            "reason": "subject and latest_message are required"
        }), 400

    metadata = data.get("metadata") or {}
    attachments = metadata.get("attachments") or []

    classification = detect_intent(
        latest_message,
        subject,
        metadata={
            "order_number": metadata.get("order_number"),
            "product": metadata.get("product"),
            "attachments": attachments,
        },
    )

    # 🔴 LLM MUST ALWAYS RUN — NO FLAGS, NO GUARDS
    draft = generate_draft(
        subject=subject,
        latest_message=latest_message,
        customer_name=data.get("customer_name"),
        conversation_history=conversation_history,
        classification=classification,
        metadata=metadata,
    )

    return jsonify({
        "draft_available": True,
        "auto_send_eligible": False,
        "confidence": autosend_confidence,
        **draft,
    }), 200


    # -----------------------------
    # Parse JSON
    # -----------------------------
    try:
        data = request.get_json()
    except Exception:
        return error_response(
            code="malformed_json",
            message="Request body must be valid JSON",
            status=400
        )

    if not data:
        return error_response(
            code="malformed_json",
            message="Request body must be valid JSON",
            status=400
        )

    # -----------------------------
    # Payload size guard
    # -----------------------------
    if request.content_length and request.content_length > MAX_PAYLOAD_BYTES:
        return error_response(
            code="payload_too_large",
            message=f"Request exceeds maximum size of {MAX_PAYLOAD_BYTES} bytes",
            details={
                "request_size_bytes": request.content_length,
                "max_size_bytes": MAX_PAYLOAD_BYTES
            },
            status=400
        )

    # -----------------------------
    # Required fields
    # -----------------------------
    required_fields = ['subject', 'latest_message', 'conversation_history']
    missing = []

    for field in required_fields:
        if field not in data or data[field] is None:
            missing.append(field)
        elif field == 'conversation_history' and not isinstance(data[field], list):
            missing.append(field)

    if missing:
        return error_response(
            code="invalid_input",
            message=f"Missing or invalid required fields: {', '.join(missing)}",
            details={
                "missing_fields": missing,
                "required_fields": required_fields
            },
            status=400
        )

    # -----------------------------
    # Field length validation
    # -----------------------------
    if len(data['subject']) > MAX_SUBJECT_LENGTH:
        return error_response(
            code="payload_too_large",
            message=f"Field 'subject' exceeds maximum length of {MAX_SUBJECT_LENGTH} characters",
            details={"field": "subject", "max_length": MAX_SUBJECT_LENGTH},
            status=400
        )

    if len(data['latest_message']) > MAX_MESSAGE_LENGTH:
        return error_response(
            code="payload_too_large",
            message=f"Field 'latest_message' exceeds maximum length of {MAX_MESSAGE_LENGTH} characters",
            details={"field": "latest_message", "max_length": MAX_MESSAGE_LENGTH},
            status=400
        )

    conversation_history = data['conversation_history']

    if len(conversation_history) > MAX_CONVERSATION_HISTORY:
        return error_response(
            code="payload_too_large",
            message=f"Conversation history exceeds maximum of {MAX_CONVERSATION_HISTORY} messages",
            details={
                "message_count": len(conversation_history),
                "max_messages": MAX_CONVERSATION_HISTORY
            },
            status=400
        )

    # -----------------------------
    # Validate conversation history items
    # -----------------------------
    for i, msg in enumerate(conversation_history):
        if not isinstance(msg, dict):
            return error_response(
                code="invalid_input",
                message=f"Message at index {i} must be an object",
                status=400
            )

        if msg.get('role') not in ['customer', 'agent']:
            return error_response(
                code="invalid_input",
                message=f"Message at index {i} must have role 'customer' or 'agent'",
                status=400
            )

        if not isinstance(msg.get('text'), str):
            return error_response(
                code="invalid_input",
                message=f"Message at index {i} must contain text",
                status=400
            )

        if len(msg['text']) > MAX_MESSAGE_LENGTH:
            return error_response(
                code="payload_too_large",
                message=f"Message at index {i} exceeds maximum length",
                status=400
            )

    # -----------------------------
    # Optional fields
    # -----------------------------
    customer_name = data.get('customer_name')
    if customer_name and len(customer_name) > MAX_CUSTOMER_NAME_LENGTH:
        return error_response(
            code="payload_too_large",
            message=f"Field 'customer_name' exceeds maximum length",
            status=400
        )

    metadata = data.get("metadata", {})
    attachments = metadata.get("attachments", []) if isinstance(metadata, dict) else []

    if len(attachments) > MAX_ATTACHMENTS:
        return error_response(
            code="payload_too_large",
            message=f"Too many attachments",
            status=400
        )

    # -----------------------------
    # Intent classification
    # -----------------------------
    classification = classify_intent(
        subject=data["subject"],
        latest_message=data["latest_message"],
        conversation_history=conversation_history
    )

    # -----------------------------
    # Draft generation
    # -----------------------------
    draft_result = {
        "type": "full",
        "response_text": generate_mock_draft(
            data["subject"],
            data["latest_message"],
            classification["primary_intent"]
        ),
        "quality_metrics": {}
    }

    # -----------------------------
    # Auto-send eligibility (SOURCE OF TRUTH)
    # -----------------------------
    auto_send_eligible = calculate_auto_send_eligible(
        classification,
        draft_result,
        attachments
    )

    requires_review = not auto_send_eligible

    # -----------------------------
    # Response payload (v1.0)
    # -----------------------------
    response = {
        "success": True,
        "request_id": f"req_{int(time.time())}",
        "timestamp": datetime.utcnow().isoformat() + "Z",

        "intent_classification": {
            "primary_intent": classification["primary_intent"],
            "secondary_intents": classification["secondary_intents"],
            "confidence": {
                "overall": classification["confidence"]["intent_confidence"],
                "label": get_confidence_label(
                    classification["confidence"]["intent_confidence"]
                ),
                "ambiguity_detected": classification["confidence"]["ambiguity_detected"]
            },
            "tone_modifier": classification["tone_modifier"],
            "safety_mode": classification["safety_mode"],
            "attempted_actions": classification["attempted_actions"],
            "signal_breakdown": classification["scores"]
        },

        "draft": {
            "type": draft_result["type"],
            "response_text": draft_result["response_text"],
            "quality_metrics": draft_result["quality_metrics"]
        },

        "agent_guidance": {
            "requires_review": requires_review,
            "auto_send_eligible": auto_send_eligible,
            "auto_send_reason": build_reason(classification, auto_send_eligible),
            "recommendation": build_recommendation(classification),
            "suggested_actions": build_suggested_actions(classification),
            "canned_responses": build_canned_response_recommendations(classification)
        }
    }

    return jsonify(response), 200


def generate_mock_draft(subject, latest_message, intent):
    """Generate contextual, deterministic draft based on intent (Option B – Step 1)"""

    if intent == "shipping_status":
        return (
            "Hi there,\n\n"
            "Thanks for reaching out — I understand wanting to get clarity on shipping, especially if timing matters.\n\n"
            "For most orders, tracking details are sent once the package is prepared for shipment. "
            "If you already received an order confirmation, that means your order is in our system and queued correctly.\n\n"
            "Could you please share your order number so I can check the current status and see whether tracking "
            "has been issued yet?\n\n"
            "Once I have that, I can give you a more specific update.\n\n"
            "Best regards,\n"
            "FutureBit Support"
        )

    elif intent == "sync_delay":
        return (
            "Hi there,\n\n"
            "Thanks for checking in — initial blockchain sync can feel unclear, especially on first setup.\n\n"
            "On Apollo devices, a long initial sync is normal. You can check progress directly in the Apollo dashboard "
            "under the Node section. If the block height is increasing, even slowly, the node is functioning as expected.\n\n"
            "A few quick things to verify:\n"
            "- Is the block height continuing to increase?\n"
            "- Does the dashboard show the node as connected?\n"
            "- Are there any visible error messages?\n\n"
            "If the block height is moving, the best next step is usually to let the sync continue uninterrupted. "
            "Initial sync can take 24–48 hours depending on connection speed.\n\n"
            "If it appears completely stalled, let me know what the dashboard shows and we can take a closer look.\n\n"
            "Best regards,\n"
            "FutureBit Support"
        )

    elif intent == "not_hashing":
        return (
            "Hi there,\n\n"
            "Thanks for reaching out — if your Apollo was running previously and has stopped hashing, it’s good that "
            "you checked in before changing anything.\n\n"
            "Before assuming a deeper issue, the first thing to confirm is whether the node is fully synced. "
            "If the node is still syncing, mining will not start yet.\n\n"
            "Could you confirm whether the dashboard shows the node as fully synced, and whether there are any error "
            "messages visible in the Miner or Node sections?\n\n"
            "Once we confirm that, we can decide on the most appropriate next step.\n\n"
            "Best regards,\n"
            "FutureBit Support"
        )

    elif intent == "setup_help":
        return (
            "Hi there,\n\n"
            "Thanks for reaching out — happy to help you get oriented.\n\n"
            "After powering on the Apollo, it typically takes a few minutes to fully boot. "
            "Once ready, you should be able to access the dashboard using `apollo.local` from a device on the same network.\n\n"
            "If that address doesn’t load, the next step is usually to confirm that the Apollo is connected via Ethernet "
            "and that your computer is on the same local network.\n\n"
            "Do you see the device listed in your router or network settings?\n\n"
            "Let me know what you’re seeing and we’ll go step by step.\n\n"
            "Best regards,\n"
            "FutureBit Support"
        )

    elif intent == "general_question":
        return (
            f"Hi there,\n\n"
            f"Thanks for reaching out with your question about:\n\"{subject}\"\n\n"
            "I’m happy to help clarify things. To make sure I give you the most relevant information, "
            "could you share a bit more detail about what you’re trying to do or decide?\n\n"
            "Once I understand that better, I can point you in the right direction.\n\n"
            "Best regards,\n"
            "FutureBit Support"
        )

    else:
        return (
            f"Hi there,\n\n"
            f"Thanks for contacting FutureBit support regarding:\n\"{subject}\"\n\n"
            "I want to make sure I understand the situation correctly before suggesting next steps. "
            "Could you provide a bit more detail about what you’re seeing or what you expected to happen?\n\n"
            "Once I have that, I’ll be able to assist more effectively.\n\n"
            "Best regards,\n"
            "FutureBit Support"
        )

def classify_intent(subject, latest_message, conversation_history):
    """
    Lightweight keyword classifier (v1.0 placeholder).
    Goal: stop shipping_status from winning when technical/support keywords exist.
    Returns: (classification_dict)
    """

    def _norm(s):
        return (s or "").strip().lower()

          # Combine all relevant text
    parts = [_norm(subject), _norm(latest_message)]
    for msg in (conversation_history or []):
        if isinstance(msg, dict) and isinstance(msg.get("text"), str):
            parts.append(_norm(msg["text"]))

    text = " ".join([p for p in parts if p])

  
    # PHASE 1.2 — intent signal normalization (LOCKED)
    text = (
        text
        .replace("’", "'")
        .replace("doesn’t", "doesn't")
        .replace("won’t", "won't")
        .replace("can’t", "can't")
    )


    # -------------------------------------------------
    # PHASE 1.2 — setup_help hard detection (LOCKED)
    # -------------------------------------------------
    setup_help_phrases = [
        "apollo.local",
        "futurebit.local",
        "doesn't load",
        "doesnt load",
        "won't load",
        "wont load",
        "can't access",
        "cannot access",
        "dashboard won't load",
        "dashboard doesnt load",
        "dashboard doesn't load",
    ]

    if any(phrase in text for phrase in setup_help_phrases):
        return {
            "primary_intent": "setup_help",
            "secondary_intents": [],
            "confidence": {
                "intent_confidence": 0.90,
                "ambiguity_detected": False,
            },
            "tone_modifier": "neutral",
            "safety_mode": "safe",
            "device_behavior_detected": False,
            "attempted_actions": [],
            "scores": {
                "setup_help": 5,
                "shipping_status": 0,
                "not_hashing": 0,
                "sync_delay": 0,
                "general_question": 0,
            },
        }



    # Keyword buckets
    shipping_kw = {
        "order", "shipping", "ship", "shipped", "tracking", "track", "delivery",
        "eta", "arrive", "arrival", "where is my", "status", "confirmation",
        "fulfilled", "fulfillment"
    }

    # “Technical” words that should block shipping from being primary
    technical_block_kw = {
        "hash", "hashing", "miner", "mining", "not hashing", "0 h/s", "hs", "h/s",
        "sync", "syncing", "node", "block", "blockchain",
        "apollo", "apollo.local", "futurebit.local", "dashboard", "web ui",
        "firmware", "update", "logs", "debug", "error", "reboot", "restart",
        "lan", "ethernet", "wifi", "ip", "router", "pool", "solo", "start miner"
    }

    not_hashing_kw = {
        "not hashing", "0 h/s", "hashrate", "h/s", "start miner", "miner won't",
        "miner wont", "mining stopped", "stopped mining", "no hashing", "hashing fine yesterday"
    }

    sync_delay_kw = {
        "not syncing", "syncing", "sync", "stuck", "blocks", "block height",
        "fully synced", "sync progress", "initial sync", "headers", "ibd"
    }

    setup_help_kw = {
        "setup", "set up", "getting started", "first time", "wizard",
        "can't access", "cannot access", "won't load", "doesn't load",
        "apollo.local", "futurebit.local", "dashboard", "browser"
    }

    # Tiny utilities
    def score(bucket):
        return sum(1 for kw in bucket if kw in text)

    # Hard guard: if ANY technical keyword exists, shipping must be heavily penalized
    technical_hits = score(technical_block_kw)

    scores = {
        "shipping_status": score(shipping_kw),
        "not_hashing": score(not_hashing_kw),
        "sync_delay": score(sync_delay_kw),
        "setup_help": score(setup_help_kw),
        "general_question": 0
    }

    # Penalize shipping if technical context exists
    if technical_hits > 0:
        scores["shipping_status"] = max(0, scores["shipping_status"] - 3)

    # Fallback if nothing matches
    top_intent = max(scores, key=scores.get)
    top_score = scores[top_intent]

    if top_score <= 0:
        primary_intent = "unknown_vague"
        intent_confidence = 0.40
        ambiguity_detected = True
    else:
        # Find runner-up to estimate ambiguity
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        runner_up_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0
        margin = top_score - runner_up_score

        primary_intent = top_intent

        # Confidence heuristic
        if margin >= 2:
            intent_confidence = 0.90
            ambiguity_detected = False
        elif margin == 1:
            intent_confidence = 0.78
            ambiguity_detected = False
        else:
            intent_confidence = 0.65
            ambiguity_detected = True

        # If technical hits exist and shipping somehow wins, force ambiguity + lower confidence
        if technical_hits > 0 and primary_intent == "shipping_status":
            intent_confidence = 0.55
            ambiguity_detected = True

    # Detect device-behavior signals (lightweight)
    device_behavior_detected = any(k in text for k in ["hot", "overheat", "overheating", "fan", "loud", "restarting", "thermal"])

    # Attempted actions (lightweight extraction)
    attempted_actions = []
    attempted_map = [
        ("reboot", "rebooted"),
        ("restart", "restarted"),
        ("update", "updated firmware"),
        ("factory reset", "factory reset"),
        ("reflash", "reflashed"),
        ("different browser", "tried different browser"),
        ("toggled", "toggled settings"),
        ("checked router", "checked router"),
    ]
    for needle, label in attempted_map:
        if needle in text:
            attempted_actions.append(label)

    classification = {
        "primary_intent": primary_intent,
        "secondary_intents": [],
        "confidence": {
            "intent_confidence": float(intent_confidence),
            "ambiguity_detected": bool(ambiguity_detected)
        },
        "tone_modifier": "neutral",
        "safety_mode": "safe",
        "device_behavior_detected": bool(device_behavior_detected),
        "attempted_actions": attempted_actions,
        "scores": scores
    }

    return classification


@ai_draft_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200


def calculate_auto_send_eligible(classification, draft_result, attachments):
    """Calculate auto-send eligibility per v1.0 contract"""
    intent = classification["primary_intent"]
    confidence = classification["confidence"]["intent_confidence"]
    safety_mode = classification["safety_mode"]
    ambiguity_detected = classification["confidence"]["ambiguity_detected"]
    draft_type = draft_result["type"]
    
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
    """Build reason text for agent guidance"""
    intent = classification["primary_intent"]
    safety_mode = classification["safety_mode"]
    confidence = classification["confidence"]["intent_confidence"]
    
    if auto_send_eligible:
        return f"High-confidence shipping inquiry ({intent}). Auto-send eligible."
    if safety_mode == "unsafe":
        return f"Diagnostic issue detected ({intent}). Request data before troubleshooting."
    if intent == "unknown_vague":
        return "Intent unclear. Request clarification from customer."
    if confidence < 0.85:
        return f"Intent is {intent} but confidence is below threshold. Manual review recommended."
    
    return "Informational request. Provide accurate information from knowledge base."


def get_confidence_label(confidence):
    """Convert confidence score to label"""
    if confidence >= 0.85:
        return "high"
    elif confidence >= 0.70:
        return "medium"
    elif confidence >= 0.50:
        return "low"
    else:
        return "very_low"


def build_recommendation(classification):
    """Build recommendation text based on classification"""
    intent = classification["primary_intent"]
    safety = classification["safety_mode"]
    
    if safety == "unsafe":
        return f"Diagnostic issue detected ({intent}). Request data before troubleshooting."
    elif intent == "unknown_vague":
        return "Intent unclear. Request clarification from customer."
    else:
        return "Informational request. Provide accurate information from knowledge base."


def build_suggested_actions(classification):
    """Build suggested actions list based on classification"""
    intent = classification["primary_intent"]
    
    actions_map = {
        "not_hashing": [
            "Request debug.log and getblockchaininfo output",
            "Review logs for error patterns",
            "Consider: Node Not Hashing Troubleshooting canned response"
        ],
        "shipping_status": [
            "Look up order in admin system",
            "Provide accurate tracking information",
            "Set realistic delivery expectations"
        ],
        "general_question": [
            "Provide educational explanation",
            "Use neutral, informative tone",
            "Reference documentation if available"
        ]
    }
    
    return actions_map.get(intent, ["Review customer message", "Provide appropriate response"])


def error_response(code, message, details=None, status=400):
    """Build standardized error response"""
    error_obj = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if details:
        error_obj["error"]["details"] = details
    
    return jsonify(error_obj), status
def build_canned_response_recommendations(classification):
    """Suggest relevant canned responses based on intent"""

    intent = classification["primary_intent"]

    canned_map = {
        "not_hashing": [
            {
                "id": "apollo_not_hashing_v1",
                "title": "Apollo Not Hashing – Initial Checks",
                "reason": "Common first-response checklist for mining issues"
            }
        ],
        "sync_delay": [
            {
                "id": "node_initial_sync_v1",
                "title": "Node Initial Sync – What’s Normal",
                "reason": "Explains expected sync behavior and timelines"
            }
        ],
        "shipping_status": [
            {
                "id": "shipping_status_v1",
                "title": "Order Shipping Status & Tracking",
                "reason": "Standard response for shipment inquiries"
            }
        ],
        "setup_help": [
            {
                "id": "apollo_setup_network_v1",
                "title": "Apollo Setup & Network Access",
                "reason": "Helps users access dashboard and verify connectivity"
            }
        ]
    }

    return canned_map.get(intent, [])

def build_canned_response_recommendations(classification):
    """Suggest relevant canned responses based on intent"""

    intent = classification["primary_intent"]

    canned_map = {
        "not_hashing": [
            {
                "id": "apollo_not_hashing_v1",
                "title": "Apollo Not Hashing – Initial Checks",
                "reason": "Common first-response checklist for mining issues"
            }
        ],
        "sync_delay": [
            {
                "id": "node_initial_sync_v1",
                "title": "Node Initial Sync – What’s Normal",
                "reason": "Explains expected sync behavior and timelines"
            }
        ],
        "shipping_status": [
            {
                "id": "shipping_status_v1",
                "title": "Order Shipping Status & Tracking",
                "reason": "Standard response for shipment inquiries"
            }
        ],
        "setup_help": [
            {
                "id": "apollo_setup_network_v1",
                "title": "Apollo Setup & Network Access",
                "reason": "Helps users access dashboard and verify connectivity"
            }
        ]
    }

    return canned_map.get(intent, [])
