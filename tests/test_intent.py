"""
Test intent classification with real-world examples
"""
import sys
sys.path.insert(0, '/home/claude/sidecar')

from intent_classifier import detect_intent

# Test cases from design spec
test_cases = [
    {
        "name": "Not hashing - clear",
        "subject": "Apollo not working",
        "message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
        "expected_intent": "not_hashing",
        "expected_safety": "unsafe"
    },
    {
        "name": "Sync delay - anxious",
        "subject": "Blockchain sync stuck",
        "message": "My node has been stuck at block 800,000 for 2 days. Is this normal?",
        "expected_intent": "sync_delay",
        "expected_safety": "unsafe"
    },
    {
        "name": "Shipping status",
        "subject": "Where is my order?",
        "message": "Where is my order #FBT-2024-1234? Ordered Apollo II last week.",
        "expected_intent": "shipping_status",
        "expected_safety": "safe"
    },
    {
        "name": "Setup help",
        "subject": "Pool configuration",
        "message": "Just received my Apollo III. How do I connect it to a mining pool?",
        "expected_intent": "setup_help",
        "expected_safety": "safe"
    },
    {
        "name": "General question",
        "subject": "Mining question",
        "message": "What's the difference between solo mining and pool mining?",
        "expected_intent": "general_question",
        "expected_safety": "safe"
    },
    {
        "name": "Too vague",
        "subject": "Help",
        "message": "My Apollo isn't working.",
        "expected_intent": "unknown_vague",
        "expected_safety": "safe"
    },
    {
        "name": "Firmware issue",
        "subject": "Update failed",
        "message": "Firmware update failed. UI won't load now.",
        "expected_intent": "firmware_issue",
        "expected_safety": "unsafe"
    },
    {
        "name": "Performance issue",
        "subject": "Device restarting",
        "message": "My Apollo keeps restarting every 30 minutes. Fans are loud.",
        "expected_intent": "performance_issue",
        "expected_safety": "unsafe"
    },
    {
        "name": "Warranty RMA",
        "subject": "Defective unit",
        "message": "Want a refund. Device was broken on arrival.",
        "expected_intent": "warranty_rma",
        "expected_safety": "safe"
    },
    {
        "name": "Device behavior override",
        "subject": "Order issue",
        "message": "My order isn't hashing. It shows 0 H/s.",
        "expected_intent": "not_hashing",
        "expected_safety": "unsafe",
        "note": "Should be not_hashing, not shipping_status (device behavior override)"
    },
    {
        "name": "Already tried multiple steps",
        "subject": "Still not working",
        "message": "Not hashing. Already tried restarting, updating firmware, and changing pools.",
        "expected_intent": "not_hashing",
        "expected_safety": "unsafe",
        "expected_actions": ["restart", "firmware_update", "pool_change"]
    },
    {
        "name": "Panic tone",
        "subject": "URGENT",
        "message": "URGENT!!! My Apollo stopped mining 3 days ago and I'm losing money!!!",
        "expected_intent": "not_hashing",
        "expected_tone": "panic"
    }
]


def run_tests():
    """Run all test cases"""
    print("Testing Intent Classification\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Subject: {test['subject']}")
        print(f"Message: {test['message']}")
        
        # Run classification
        result = detect_intent(
            subject=test['subject'],
            message=test['message']
        )
        
        # Check expectations
        checks = []
        
        # Check intent
        intent_match = result['primary_intent'] == test['expected_intent']
        checks.append(("Intent", test['expected_intent'], result['primary_intent'], intent_match))
        
        # Check safety mode
        if 'expected_safety' in test:
            safety_match = result['safety_mode'] == test['expected_safety']
            checks.append(("Safety", test['expected_safety'], result['safety_mode'], safety_match))
        
        # Check tone
        if 'expected_tone' in test:
            tone_match = result['tone_modifier'] == test['expected_tone']
            checks.append(("Tone", test['expected_tone'], result['tone_modifier'], tone_match))
        
        # Check attempted actions
        if 'expected_actions' in test:
            actions_match = set(result['attempted_actions']) == set(test['expected_actions'])
            checks.append(("Actions", test['expected_actions'], result['attempted_actions'], actions_match))
        
        # Print results
        test_passed = all(check[3] for check in checks)
        
        for check_name, expected, actual, match in checks:
            status = "✅" if match else "❌"
            print(f"  {status} {check_name}: {actual} (expected: {expected})")
        
        print(f"  Confidence: {result['confidence']['intent_confidence']}")
        print(f"  Device behavior: {result['device_behavior_detected']}")
        print(f"  Top scores: {result['scores']}")
        
        if test_passed:
            passed += 1
            print("  ✅ PASSED")
        else:
            failed += 1
            print("  ❌ FAILED")
    
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
