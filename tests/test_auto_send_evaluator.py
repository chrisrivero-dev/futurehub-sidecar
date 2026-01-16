# tests/test_auto_send_evaluator.py

"""
Unit tests for auto-send eligibility evaluator
Day 6: Test pure function logic
"""

import unittest
from utils.auto_send_evaluator import (
    evaluate_auto_send_eligibility,
    SAFE_INTENTS,
    UNSAFE_INTENTS,
    CONFIDENCE_THRESHOLD
)


class TestAutoSendEvaluator(unittest.TestCase):
    
    def test_safe_intent_high_confidence(self):
        """Safe intent with high confidence should be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=0.92,
            has_attachments=False,
            has_logs=False,
            ticket_status='open'
        )
        self.assertTrue(eligible)
        self.assertIn('Eligible', reason)
    
    def test_unsafe_intent(self):
        """Unsafe intent should never be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='not_hashing',
            confidence=0.95,
            has_attachments=False,
            has_logs=False,
            ticket_status='open'
        )
        self.assertFalse(eligible)
        self.assertIn('unsafe', reason.lower())
    
    def test_low_confidence(self):
        """Low confidence should not be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=0.70,
            has_attachments=False,
            has_logs=False,
            ticket_status='open'
        )
        self.assertFalse(eligible)
        self.assertIn('below threshold', reason)
    
    def test_has_attachments(self):
        """Tickets with attachments should not be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=0.92,
            has_attachments=True,
            has_logs=False,
            ticket_status='open'
        )
        self.assertFalse(eligible)
        self.assertIn('attachments', reason)
    
    def test_has_logs(self):
        """Tickets with logs should not be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=0.92,
            has_attachments=False,
            has_logs=True,
            ticket_status='open'
        )
        self.assertFalse(eligible)
        self.assertIn('log', reason.lower())
    
    def test_non_open_status(self):
        """Non-open tickets should not be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=0.92,
            has_attachments=False,
            has_logs=False,
            ticket_status='resolved'
        )
        self.assertFalse(eligible)
        self.assertIn('status', reason)
    
    def test_no_intent(self):
        """Missing intent should not be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent=None,
            confidence=0.92,
            has_attachments=False,
            has_logs=False,
            ticket_status='open'
        )
        self.assertFalse(eligible)
        self.assertIn('No intent', reason)
    
    def test_no_confidence(self):
        """Missing confidence should not be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=None,
            has_attachments=False,
            has_logs=False,
            ticket_status='open'
        )
        self.assertFalse(eligible)
        self.assertIn('No confidence', reason)
    
    def test_threshold_boundary(self):
        """Confidence exactly at threshold should be eligible"""
        eligible, reason = evaluate_auto_send_eligibility(
            intent='shipping_status',
            confidence=CONFIDENCE_THRESHOLD,
            has_attachments=False,
            has_logs=False,
            ticket_status='open'
        )
        self.assertTrue(eligible)
    
    def test_all_safe_intents(self):
        """All defined safe intents should pass with valid conditions"""
        for intent in SAFE_INTENTS:
            eligible, reason = evaluate_auto_send_eligibility(
                intent=intent,
                confidence=0.90,
                has_attachments=False,
                has_logs=False,
                ticket_status='open'
            )
            self.assertTrue(eligible, f"Intent '{intent}' should be eligible but got: {reason}")


if __name__ == '__main__':
    unittest.main()