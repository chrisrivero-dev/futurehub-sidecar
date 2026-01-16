"""
Comprehensive API example - shows full draft generation in action
"""
import sys
import json
sys.path.insert(0, '/home/claude/sidecar')

from app import app

def test_full_api_response():
    """Show complete API response with real draft"""
    
    with app.test_client() as client:
        # Example 1: Not hashing diagnostic issue
        print("=" * 80)
        print("EXAMPLE 1: Diagnostic Issue (not_hashing)")
        print("=" * 80)
        
        payload = {
            "subject": "Apollo not working",
            "latest_message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
            "conversation_history": [{
                "from": "customer",
                "message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
                "timestamp": "2026-01-13T10:00:00Z"
            }],
            "customer": {
                "name": "Mark Thompson",
                "email": "mark@example.com"
            },
            "metadata": {
                "product": "Apollo II",
                "priority": "high"
            }
        }
        
        response = client.post(
            '/api/v1/draft',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        data = response.get_json()
        
        print(f"\nIntent: {data['intent_classification']['primary_intent']}")
        print(f"Safety mode: {data['intent_classification']['safety_mode']}")
        print(f"Confidence: {data['intent_classification']['confidence']['overall']}")
        print(f"Tone: {data['intent_classification']['tone_modifier']}")
        print(f"Attempted actions: {data['intent_classification']['attempted_actions']}")
        print(f"\nDraft type: {data['draft']['type']}")
        print(f"\nGenerated draft:\n{'-' * 80}")
        print(data['draft']['response_text'])
        print(f"{'-' * 80}")
        print(f"\nCanned response: {data['agent_guidance']['canned_response_suggestion']['category']}")
        print(f"Reason: {data['agent_guidance']['canned_response_suggestion']['reason']}")
        
        # Example 2: Shipping status (safe intent)
        print("\n\n" + "=" * 80)
        print("EXAMPLE 2: Shipping Status (safe intent)")
        print("=" * 80)
        
        payload = {
            "subject": "Where is my order?",
            "latest_message": "I ordered an Apollo II last week. Where is it?",
            "conversation_history": [{
                "from": "customer",
                "message": "I ordered an Apollo II last week. Where is it?",
                "timestamp": "2026-01-13T11:00:00Z"
            }],
            "customer": {
                "name": "Sarah Chen",
                "email": "sarah@example.com"
            },
            "metadata": {
                "order_number": "FBT-2024-5678",
                "product": "Apollo II"
            }
        }
        
        response = client.post(
            '/api/v1/draft',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        data = response.get_json()
        
        print(f"\nIntent: {data['intent_classification']['primary_intent']}")
        print(f"Safety mode: {data['intent_classification']['safety_mode']}")
        print(f"Confidence: {data['intent_classification']['confidence']['overall']}")
        print(f"\nDraft type: {data['draft']['type']}")
        print(f"\nGenerated draft:\n{'-' * 80}")
        print(data['draft']['response_text'])
        print(f"{'-' * 80}")
        print(f"\nRequires review: {data['agent_guidance']['requires_review']}")
        
        # Example 3: Escalation (3+ steps tried)
        print("\n\n" + "=" * 80)
        print("EXAMPLE 3: Escalation (customer tried 3+ steps)")
        print("=" * 80)
        
        payload = {
            "subject": "Still not working",
            "latest_message": "Not hashing. Already tried restarting, updating firmware, and changing pools.",
            "conversation_history": [{
                "from": "customer",
                "message": "Not hashing. Already tried restarting, updating firmware, and changing pools.",
                "timestamp": "2026-01-13T12:00:00Z"
            }],
            "customer": {
                "name": "Chris Martinez",
                "email": "chris@example.com"
            },
            "metadata": {
                "product": "Apollo II"
            }
        }
        
        response = client.post(
            '/api/v1/draft',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        data = response.get_json()
        
        print(f"\nIntent: {data['intent_classification']['primary_intent']}")
        print(f"Safety mode: {data['intent_classification']['safety_mode']}")
        print(f"Attempted actions: {data['intent_classification']['attempted_actions']}")
        print(f"\nDraft type: {data['draft']['type']}")
        print(f"\nGenerated draft:\n{'-' * 80}")
        print(data['draft']['response_text'])
        print(f"{'-' * 80}")
        
        print("\n✅ All examples complete!")


if __name__ == '__main__':
    test_full_api_response()
