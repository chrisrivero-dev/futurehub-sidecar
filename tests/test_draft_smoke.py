"""
Smoke test for ai/draft_generator.py
Verifies generate_draft() returns real content, not the generic fallback.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FALLBACK_TEXT = "I can help \u2014 could you clarify what you're looking for?"


class TestDraftGeneratorSmoke(unittest.TestCase):

    @patch("ai.draft_generator.generate_llm_response")
    def test_generate_draft_returns_non_fallback(self, mock_llm):
        """generate_draft() must return real content, not the generic fallback."""
        mock_llm.return_value = {
            "text": "Your order is being prepared and tracking will be sent shortly.",
            "model": "mock",
            "llm_used": True,
        }

        from ai.draft_generator import generate_draft

        result = generate_draft(
            subject="Order status",
            latest_message="Where is my tracking?",
            customer_name="Chris",
        )

        self.assertIsInstance(result, dict, "generate_draft must return a dict")
        self.assertIn("response_text", result, "result must contain response_text")

        text = result["response_text"]
        self.assertIsInstance(text, str, "response_text must be a string")
        self.assertTrue(len(text.strip()) > 0, "response_text must not be empty")
        self.assertNotEqual(
            text.strip(),
            FALLBACK_TEXT,
            "response_text must NOT be the generic fallback",
        )

    def test_helper_stubs_return_strings(self):
        """All stub helpers must return draft_text unchanged, never None."""
        from ai.draft_generator import (
            enrich_with_knowledge,
            apply_reasoning_style,
            apply_draft_constraints,
        )

        sample = "Test draft text."

        r1 = enrich_with_knowledge(draft_text=sample, intent="shipping_status", mode="explanatory")
        self.assertIsInstance(r1, str, "enrich_with_knowledge must return a string")
        self.assertEqual(r1, sample)

        r2 = apply_reasoning_style(draft_text=sample, intent="shipping_status", mode="explanatory")
        self.assertIsInstance(r2, str, "apply_reasoning_style must return a string")
        self.assertEqual(r2, sample)

        r3 = apply_draft_constraints(draft_text=sample, intent="shipping_status", tone_modifier=None)
        self.assertIsInstance(r3, str, "apply_draft_constraints must return a string")
        self.assertTrue(len(r3) > 0, "apply_draft_constraints must not return empty")


if __name__ == "__main__":
    unittest.main()
