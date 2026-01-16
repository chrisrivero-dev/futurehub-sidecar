"""
Test draft generation with various intents
"""
import sys
sys.path.insert(0, '/home/claude/sidecar')

from intent_classifier import detect_intent
from draft_generator import generate_draft

# Test cases
test_cases = [
    {
        "name": "Not hashing - diagnostic draft",
        "subject": "Apollo not working",
        "message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
        "customer_name": "Mark",
        "metadata": {"product": "Apollo II"},
        "expected_type": "clarification_only",
        "should_contain": ["understand", "debug.log", "getblockchaininfo", "already tried restarting"]
    },
    {
        "name": "Shipping status - with order number",
        "subject": "Where is my order?",
        "message": "Where is my order? I ordered last week.",
        "customer_name": "Sarah",
        "metadata": {"order_number": "FBT-2024-1234"},
        "expected_type": "full",
        "should_contain": ["Hi Sarah", "FBT-2024-1234", "within 2 hours"]
    },
    {
        "name": "Setup help - needs clarification",
        "subject": "How to configure",
        "message": "Just got my Apollo III. How do I set it up?",
        "customer_name": "Alex",
        "metadata": {"product": "Apollo III"},
        "expected_type": "full",
        "should_contain": ["Apollo III", "solo mining or pool mining"]
    },
    {
        "name": "Escalation - tried 3+ steps",
        "subject": "Still broken",
        "message": "Not hashing. Already tried restarting, updating firmware, and changing pools.",
        "customer_name": "Chris",
        "metadata": {"product": "Apollo II"},
        "expected_type": "escalation",
        "should_contain": ["already tried", "restarting, updating firmware, and changing pools", "thorough troubleshooting"]
    },
    {
        "name": "Unknown vague - clarification",
        "subject": "Help",
        "message": "My Apollo isn't working.",
        "customer_name": None,
        "metadata": {},
        "expected_type": "clarification_only",
        "should_contain": ["understand your situation", "powering on", "0 H/s"]
    },
    {
        "name": "Panic tone - adds reassurance",
        "subject": "URGENT",
        "message": "URGENT!!! My Apollo stopped mining 3 days ago!!!",
        "customer_name": "Jamie",
        "metadata": {"product": "Apollo II"},
        "expected_type": "clarification_only",
        "should_contain": ["Jamie", "understand this is urgent", "need help right away"]
    },
    {
        "name": "Sync delay - diagnostic",
        "subject": "Sync stuck",
        "message": "My node is stuck at block 800,000 for 2 days.",
        "customer_name": "Taylor",
        "metadata": {"product": "Apollo II"},
        "expected_type": "clarification_only",
        "should_contain": ["sync issues", "getblockchaininfo", "block number"]
    },
    {
        "name": "Warranty RMA - process explanation",
        "subject": "Defective device",
        "message": "Want a refund. Device broken on arrival.",
        "customer_name": "Jordan",
        "metadata": {},
        "expected_type": "full",
        "should_contain": ["warranty", "what's happening with the device", "within 4 hours"]
    }
]


def run_tests():
    """Run all draft generation tests"""
    print("Testing Draft Generation\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {test['message'][:60]}...")
        
        # Classify intent
        classification = detect_intent(
            subject=test['subject'],
            message=test['message'],
            metadata=test.get('metadata', {})
        )
        
        # Generate draft
        draft_result = generate_draft(
            classification=classification,
            customer_name=test.get('customer_name'),
            metadata=test.get('metadata', {})
        )
        
        # Check draft type
        type_match = draft_result['type'] == test['expected_type']
        print(f"  Draft type: {draft_result['type']} (expected: {test['expected_type']}) {'✅' if type_match else '❌'}")
        
        # Check required content
        draft_text = draft_result['response_text']
        content_checks = []
        for required in test['should_contain']:
            present = required.lower() in draft_text.lower()
            content_checks.append(present)
            status = "✅" if present else "❌"
            print(f"  {status} Contains '{required}': {present}")
        
        # Check quality metrics
        metrics = draft_result['quality_metrics']
        print(f"  Quality metrics:")
        print(f"    Structure: {metrics['structure_score']}")
        print(f"    Tone: {metrics['tone_appropriateness']}")
        print(f"    Hallucination risk: {metrics['hallucination_risk']}")
        
        # Check canned response recommendation for unsafe intents
        if classification['safety_mode'] == 'unsafe':
            has_canned = draft_result.get('canned_response_suggestion') is not None
            print(f"  Canned response: {'✅' if has_canned else '❌'} {draft_result.get('canned_response_suggestion', {}).get('category', 'None')}")
        
        # Overall pass/fail
        test_passed = type_match and all(content_checks)
        
        if test_passed:
            passed += 1
            print("  ✅ PASSED")
        else:
            failed += 1
            print("  ❌ FAILED")
            print(f"\n  Generated draft:\n  {draft_text[:200]}...\n")
    
    print("\n" + "=" * 80)
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} tests failed")
        return 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
