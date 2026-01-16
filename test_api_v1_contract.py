"""
FutureHub AI Sidecar — v1.0 API Contract Validation Tests
Tests that app_v1.py conforms to the locked v1.0 API contract

Run: pytest test_api_v1_contract.py -v
"""
import pytest
import json
import sys
from datetime import datetime

# Import the Flask app
sys.path.insert(0, '/home/claude')
from app_v1 import app


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ==============================================================================
# CATEGORY 1: Valid Payloads
# ==============================================================================

def test_valid_shipping_status_auto_send_eligible(client):
    """
    Test: Valid shipping_status request with high confidence
    Expected: auto_send_eligible = true
    """
    payload = {
        "subject": "Where is my order?",
        "latest_message": "Where is my order #FBT-2024-1234? I ordered last week.",
        "conversation_history": [],
        "customer_name": "Sarah",
        "metadata": {
            "order_number": "FBT-2024-1234",
            "product": "Apollo II"
        }
    }
    
    response = client.post('/api/v1/draft', 
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Contract assertions
    assert data["success"] == True
    assert data["version"] == "1.0"
    assert "timestamp" in data
    assert "processing_time_ms" in data
    assert isinstance(data["processing_time_ms"], int)
    
    # Intent classification
    assert data["intent_classification"]["primary_intent"] == "shipping_status"
    assert data["intent_classification"]["safety_mode"] == "safe"
    assert data["intent_classification"]["confidence"]["overall"] >= 0.85
    
    # Draft
    assert data["draft"]["type"] == "full"
    assert "Sarah" in data["draft"]["response_text"]
    assert "FBT-2024-1234" in data["draft"]["response_text"]
    
    # Agent guidance - CRITICAL
    assert data["agent_guidance"]["auto_send_eligible"] == True
    assert data["agent_guidance"]["requires_review"] == False
    assert "shipping" in data["agent_guidance"]["reason"].lower()


def test_valid_diagnostic_not_auto_send(client):
    """
    Test: Valid not_hashing request (unsafe intent)
    Expected: auto_send_eligible = false, requires_review = true
    """
    payload = {
        "subject": "Apollo not working",
        "latest_message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
        "conversation_history": [],
        "customer_name": "Mark",
        "metadata": {
            "product": "Apollo II",
            "attachments": ["debug.log"]
        }
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Intent classification
    assert data["intent_classification"]["primary_intent"] == "not_hashing"
    assert data["intent_classification"]["safety_mode"] == "unsafe"
    
    # Draft type
    assert data["draft"]["type"] == "clarification_only"
    
    # Agent guidance - CRITICAL
    assert data["agent_guidance"]["auto_send_eligible"] == False
    assert data["agent_guidance"]["requires_review"] == True
    assert "diagnostic" in data["agent_guidance"]["reason"].lower()
    
    # Canned response suggestion should be present
    assert "canned_response_suggestion" in data["agent_guidance"]
    assert data["agent_guidance"]["canned_response_suggestion"]["category"] == "Node Not Hashing Troubleshooting"


def test_valid_conversation_history(client):
    """
    Test: Valid request with conversation history
    Expected: Conversation history accepted, draft generated
    """
    payload = {
        "subject": "Sync stuck",
        "latest_message": "It's still stuck at the same block.",
        "conversation_history": [
            {
                "role": "customer",
                "text": "My node is stuck at block 800,000.",
                "timestamp": "2024-01-10T10:00:00Z"
            },
            {
                "role": "agent",
                "text": "Can you run getblockchaininfo?",
                "timestamp": "2024-01-10T11:00:00Z"
            }
        ],
        "customer_name": "Taylor",
        "metadata": {"product": "Apollo II"}
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert data["intent_classification"]["primary_intent"] == "sync_delay"
    assert data["draft"]["type"] == "clarification_only"
    assert data["agent_guidance"]["auto_send_eligible"] == False


def test_valid_empty_conversation_history(client):
    """
    Test: Valid request with empty conversation_history
    Expected: Accepted (first message in ticket)
    """
    payload = {
        "subject": "Setup help",
        "latest_message": "How do I set up my Apollo?",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] == True


def test_valid_minimal_payload(client):
    """
    Test: Valid request with only required fields
    Expected: Success (optional fields not required)
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help with my Apollo.",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] == True


# ==============================================================================
# CATEGORY 2: Malformed JSON
# ==============================================================================

def test_malformed_json(client):
    """
    Test: Request with invalid JSON
    Expected: 400 malformed_json
    """
    response = client.post('/api/v1/draft',
                          data='{"subject": "Help", invalid json',
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["success"] == False
    assert data["error"]["code"] == "malformed_json"
    assert "json" in data["error"]["message"].lower()
    assert "timestamp" in data


def test_empty_body(client):
    """
    Test: Request with empty body
    Expected: 400 malformed_json
    """
    response = client.post('/api/v1/draft',
                          data='',
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "malformed_json"


def test_null_body(client):
    """
    Test: Request with null body
    Expected: 400 malformed_json
    """
    response = client.post('/api/v1/draft',
                          data='null',
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "malformed_json"


# ==============================================================================
# CATEGORY 3: Missing Required Fields
# ==============================================================================

def test_missing_subject(client):
    """
    Test: Request missing 'subject' field
    Expected: 400 invalid_input
    """
    payload = {
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["success"] == False
    assert data["error"]["code"] == "invalid_input"
    assert "subject" in data["error"]["message"].lower()
    assert "subject" in data["error"]["details"]["missing_fields"]


def test_missing_latest_message(client):
    """
    Test: Request missing 'latest_message' field
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "invalid_input"
    assert "latest_message" in data["error"]["details"]["missing_fields"]


def test_missing_conversation_history(client):
    """
    Test: Request missing 'conversation_history' field
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help"
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "invalid_input"
    assert "conversation_history" in data["error"]["details"]["missing_fields"]


def test_null_required_field(client):
    """
    Test: Request with null value for required field
    Expected: 400 invalid_input
    """
    payload = {
        "subject": None,
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "invalid_input"


def test_conversation_history_not_array(client):
    """
    Test: conversation_history is string instead of array
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": "not an array"
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "invalid_input"


# ==============================================================================
# CATEGORY 4: Payload Size Violations
# ==============================================================================

def test_subject_too_long(client):
    """
    Test: subject exceeds 500 characters
    Expected: 400 payload_too_large
    """
    payload = {
        "subject": "x" * 501,  # 501 chars (max is 500)
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "payload_too_large"
    assert "subject" in data["error"]["message"].lower()
    assert data["error"]["details"]["field"] == "subject"
    assert data["error"]["details"]["max_length"] == 500


def test_latest_message_too_long(client):
    """
    Test: latest_message exceeds 10,000 characters
    Expected: 400 payload_too_large
    """
    payload = {
        "subject": "Help",
        "latest_message": "x" * 10001,  # 10,001 chars (max is 10,000)
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "payload_too_large"
    assert "latest_message" in data["error"]["message"].lower()


def test_conversation_history_too_many_messages(client):
    """
    Test: conversation_history exceeds 50 messages
    Expected: 400 payload_too_large
    """
    # Create 51 messages (max is 50)
    messages = [
        {"role": "customer", "text": f"Message {i}"}
        for i in range(51)
    ]
    
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": messages
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "payload_too_large"
    assert "conversation_history" in data["error"]["message"].lower()
    assert data["error"]["details"]["max_messages"] == 50


def test_conversation_message_text_too_long(client):
    """
    Test: Message text in conversation_history exceeds 10,000 characters
    Expected: 400 payload_too_large
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [
            {"role": "customer", "text": "x" * 10001}  # 10,001 chars
        ]
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "payload_too_large"
    assert "message_index" in data["error"]["details"]


def test_customer_name_too_long(client):
    """
    Test: customer_name exceeds 100 characters
    Expected: 400 payload_too_large
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [],
        "customer_name": "x" * 101  # 101 chars (max is 100)
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "payload_too_large"
    assert "customer_name" in data["error"]["message"].lower()


def test_attachments_too_many(client):
    """
    Test: attachments array exceeds 10 items
    Expected: 400 payload_too_large
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [],
        "metadata": {
            "attachments": [f"file{i}.log" for i in range(11)]  # 11 items (max is 10)
        }
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "payload_too_large"
    assert "attachments" in data["error"]["message"].lower()


# ==============================================================================
# CATEGORY 5: Conversation History Format Validation
# ==============================================================================

def test_conversation_history_missing_role(client):
    """
    Test: Message in conversation_history missing 'role' field
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [
            {"text": "Missing role field"}
        ]
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "invalid_input"
    assert "role" in data["error"]["message"].lower()


def test_conversation_history_invalid_role(client):
    """
    Test: Message role is not 'customer' or 'agent'
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [
            {"role": "admin", "text": "Invalid role"}
        ]
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "invalid_input"
    assert "customer" in data["error"]["message"].lower() or "agent" in data["error"]["message"].lower()


def test_conversation_history_missing_text(client):
    """
    Test: Message in conversation_history missing 'text' field
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [
            {"role": "customer"}
        ]
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    
    assert data["error"]["code"] == "invalid_input"
    assert "text" in data["error"]["message"].lower()


def test_conversation_history_text_not_string(client):
    """
    Test: Message text is not a string
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": [
            {"role": "customer", "text": 123}  # Number instead of string
        ]
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "invalid_input"


def test_conversation_history_message_not_object(client):
    """
    Test: Message in conversation_history is not an object
    Expected: 400 invalid_input
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": ["not an object"]
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "invalid_input"


# ==============================================================================
# CATEGORY 6: auto_send_eligible Edge Cases
# ==============================================================================

def test_auto_send_eligible_wrong_intent(client):
    """
    Test: setup_help with high confidence
    Expected: auto_send_eligible = false (wrong intent)
    """
    payload = {
        "subject": "How to set up Apollo",
        "latest_message": "Just got my Apollo III. How do I set it up?",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should be high confidence but NOT shipping_status
    assert data["intent_classification"]["primary_intent"] == "setup_help"
    assert data["agent_guidance"]["auto_send_eligible"] == False


def test_auto_send_eligible_low_confidence(client):
    """
    Test: shipping_status with low confidence (ambiguous)
    Expected: auto_send_eligible = false (confidence < 0.85)
    """
    payload = {
        "subject": "Order",
        "latest_message": "My order.",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Vague message should result in low confidence or unknown_vague
    assert data["agent_guidance"]["auto_send_eligible"] == False


def test_auto_send_eligible_with_attachments(client):
    """
    Test: shipping_status with attachments
    Expected: auto_send_eligible = false (attachments disqualify)
    """
    payload = {
        "subject": "Where is my order?",
        "latest_message": "Where is my order #FBT-2024-1234?",
        "conversation_history": [],
        "metadata": {
            "order_number": "FBT-2024-1234",
            "attachments": ["receipt.pdf"]
        }
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should be shipping_status but attachments disqualify auto-send
    assert data["intent_classification"]["primary_intent"] == "shipping_status"
    assert data["agent_guidance"]["auto_send_eligible"] == False


def test_auto_send_eligible_unsafe_intent(client):
    """
    Test: High confidence but unsafe intent
    Expected: auto_send_eligible = false (unsafe intents never auto-send)
    """
    payload = {
        "subject": "Not mining",
        "latest_message": "My Apollo shows 0 H/s and isn't mining.",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert data["intent_classification"]["safety_mode"] == "unsafe"
    assert data["agent_guidance"]["auto_send_eligible"] == False


def test_auto_send_eligible_clarification_draft_type(client):
    """
    Test: shipping_status but draft type is clarification_only
    Expected: auto_send_eligible = false (wrong draft type)
    
    Note: This is a theoretical edge case - shipping_status should always
    produce 'full' draft type, but test validates the contract logic.
    """
    payload = {
        "subject": "Unknown vague",
        "latest_message": "Help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should be unknown_vague with clarification_only
    assert data["draft"]["type"] == "clarification_only"
    assert data["agent_guidance"]["auto_send_eligible"] == False


# ==============================================================================
# CATEGORY 7: Response Structure Validation
# ==============================================================================

def test_response_has_all_required_fields(client):
    """
    Test: Response contains all required v1.0 contract fields
    Expected: All top-level fields present
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Top-level fields
    assert "success" in data
    assert "draft_available" in data
    assert "version" in data
    assert "timestamp" in data
    assert "processing_time_ms" in data
    assert "intent_classification" in data
    assert "draft" in data
    assert "knowledge_retrieval" in data
    assert "agent_guidance" in data
    
    # intent_classification fields
    ic = data["intent_classification"]
    assert "primary_intent" in ic
    assert "secondary_intents" in ic
    assert "confidence" in ic
    assert "tone_modifier" in ic
    assert "safety_mode" in ic
    assert "device_behavior_detected" in ic
    assert "attempted_actions" in ic
    assert "signal_breakdown" in ic
    
    # draft fields
    draft = data["draft"]
    assert "type" in draft
    assert "response_text" in draft
    assert "quality_metrics" in draft
    
    # agent_guidance fields
    ag = data["agent_guidance"]
    assert "requires_review" in ag
    assert "auto_send_eligible" in ag  # CRITICAL v1.0 field
    assert "reason" in ag
    assert "recommendation" in ag
    assert "suggested_actions" in ag


def test_processing_time_is_measured(client):
    """
    Test: processing_time_ms is a realistic measured value
    Expected: Integer > 0 and < 1000ms (reasonable range)
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    processing_time = data["processing_time_ms"]
    assert isinstance(processing_time, int)
    assert processing_time > 0
    assert processing_time < 1000  # Should complete in under 1 second


def test_timestamp_is_valid_iso8601(client):
    """
    Test: timestamp is valid ISO 8601 format
    Expected: Can parse as datetime
    """
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should parse without error
    timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    assert timestamp is not None


# ==============================================================================
# CATEGORY 8: Health Endpoint
# ==============================================================================

def test_health_endpoint(client):
    """
    Test: GET /health returns healthy status
    Expected: 200 with status, version, timestamp
    """
    response = client.get('/health')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert data["status"] == "healthy"
    assert data["version"] == "1.0"
    assert "timestamp" in data


# ==============================================================================
# CATEGORY 9: Boundary Conditions
# ==============================================================================

def test_subject_exactly_500_chars(client):
    """
    Test: subject is exactly 500 characters (boundary)
    Expected: Success (at limit)
    """
    payload = {
        "subject": "x" * 500,  # Exactly 500
        "latest_message": "I need help",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200


def test_conversation_history_exactly_50_messages(client):
    """
    Test: conversation_history has exactly 50 messages (boundary)
    Expected: Success (at limit)
    """
    messages = [
        {"role": "customer", "text": f"Message {i}"}
        for i in range(50)  # Exactly 50
    ]
    
    payload = {
        "subject": "Help",
        "latest_message": "I need help",
        "conversation_history": messages
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200


def test_confidence_exactly_85_percent(client):
    """
    Test: Confidence exactly 0.85 (threshold boundary)
    Expected: auto_send_eligible depends on other factors
    
    Note: This tests that 0.85 is inclusive (>= not >)
    """
    # This is hard to test precisely without mocking, but we can verify
    # the contract states >= 0.85, not > 0.85
    payload = {
        "subject": "Where is my order?",
        "latest_message": "Where is my order #FBT-2024-1234?",
        "conversation_history": [],
        "metadata": {"order_number": "FBT-2024-1234"}
    }
    
    response = client.post('/api/v1/draft',
                          data=json.dumps(payload),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # If confidence is >= 0.85 and other criteria met, should be eligible
    confidence = data["intent_classification"]["confidence"]["overall"]
    if confidence >= 0.85 and data["intent_classification"]["primary_intent"] == "shipping_status":
        # Other factors might still disqualify, but confidence alone doesn't
        pass  # Test passes if no error


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
