#!/usr/bin/env python3
"""
Draft behavior integration tests for FutureHub Sidecar.

Goals:
- Use the SAME endpoint & payload shape as the UI: POST /api/v1/draft
- Assert "it answers" (non-empty draft text), not auto-send eligibility
- Print useful debug if server returns HTML / 500s

Usage:
  python scripts/draft_behavior_tests.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


API_URL = "http://127.0.0.1:5000/api/v1/draft"
TIMEOUT_SECS = 20


@dataclass
class TestCase:
    id: str
    name: str
    subject: str
    latest_message: str
    expect_contains_any: Tuple[str, ...]  # lowercase substrings
    expect_question: bool = False         # expects "?" anywhere in draft text


def _post_json(url: str, payload: Dict[str, Any]) -> Tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return 0, str(e)


def _extract_draft_text(api_json: Dict[str, Any]) -> str:
    """
    Normalize all known backend shapes to a single string for assertions.
    UI works off api_json["draft"]["response_text"].

    Observed shapes:
      draft.response_text = "string"
      draft.response_text = {"text": "...", "llm_used": true, ...}
      OR sometimes response_text exists at top-level for older paths.
    """
    # Preferred: {"draft": {"response_text": ...}}
    draft = api_json.get("draft")
    if isinstance(draft, dict):
        rt = draft.get("response_text")
        if isinstance(rt, str):
            return rt.strip()
        if isinstance(rt, dict):
            t = rt.get("text")
            if isinstance(t, str):
                return t.strip()

    # Fallback: {"response_text": "..."} legacy
    rt2 = api_json.get("response_text")
    if isinstance(rt2, str):
        return rt2.strip()
    if isinstance(rt2, dict):
        t = rt2.get("text")
        if isinstance(t, str):
            return t.strip()

    return ""


def _is_html(s: str) -> bool:
    s2 = (s or "").lstrip().lower()
    return s2.startswith("<!doctype html") or s2.startswith("<html")


def run() -> int:
    tests = [
        # NOTE: These expectations are aligned with your CURRENT intent logic:
        # "order/shipping/tracking" => shipping_status => explanatory => should ask for order #
        TestCase(
            id="T1",
            name="Where is my order",
            subject="order",
            latest_message="I ordered the Solo Node 5 minutes after launch and still haven’t received any shipping email. Has anything shipped yet?",
            expect_contains_any=("order", "shipping", "email", "tracking"),
            expect_question=False,
        ),
        TestCase(
            id="T9",
            name="Angry shipping escalation",
            subject="order",
            latest_message="This is honestly ridiculous. Why do you keep saying next week? Just be honest — when will it ACTUALLY ship?",
            expect_contains_any=("order", "shipping", "update", "status"),
            expect_question=True,  # should ask for order number/details
        ),
        # Hashing / setup should NEVER 500; it can be review-required, but must answer with text
        TestCase(
            id="H1",
            name="Not hashing after reboot",
            subject="hashing",
            latest_message="My Apollo II isn’t hashing. I already rebooted it twice and it’s still not working.",
            expect_contains_any=("hash", "dashboard", "version", "what", "confirm"),
            expect_question=True,
        ),
        TestCase(
            id="S1",
            name="apollo.local not loading",
            subject="setup",
            latest_message="I tried going to apollo.local but nothing loads. I’m not very technical. Can you help?",
            expect_contains_any=("apollo.local", "network", "ip", "router", "confirm", "dashboard", "status"),
            expect_question=True,
        ),
        TestCase(
            id="R1",
            name="Crypto refund request",
            subject="refund",
            latest_message="I want a refund for my order. I paid with crypto yesterday.",
            expect_contains_any=("refund", "order", "details"),
            expect_question=True,  # should ask for order number / transaction / email, etc.
        ),
    ]

    print("\n=== DRAFT GENERATOR TEST RUN (HTTP) ===\n")
    failing = 0

    for tc in tests:
        payload = {
            "subject": tc.subject,
            "latest_message": tc.latest_message,
            "conversation_history": [],  # UI sends empty unless you add it
        }

        t0 = time.time()
        status, body = _post_json(API_URL, payload)
        ms = int((time.time() - t0) * 1000)

        if status == 0:
            failing += 1
            print(f"❌ [{tc.id}] {tc.name} — HTTP 0")
            print(body, "\n")
            continue

        if status != 200:
            failing += 1
            print(f"❌ [{tc.id}] {tc.name} — HTTP {status}")
            if _is_html(body):
                # show first chunk to avoid spam
                print(body[:600], "\n")
            else:
                print(body[:1200], "\n")
            continue

        if _is_html(body):
            failing += 1
            print(f"❌ [{tc.id}] {tc.name} — got HTML (expected JSON) ({ms}ms)")
            print(body[:600], "\n")
            continue

        try:
            data = json.loads(body)
        except Exception:
            failing += 1
            print(f"❌ [{tc.id}] {tc.name} — invalid JSON ({ms}ms)")
            print(body[:800], "\n")
            continue

        draft_text = _extract_draft_text(data)
        if not draft_text:
            failing += 1
            print(f"❌ [{tc.id}] {tc.name} — empty draft_text ({ms}ms)")
            print(json.dumps(data, indent=2)[:1200], "\n")
            continue

        low = draft_text.lower()
        if tc.expect_contains_any and not any(s in low for s in tc.expect_contains_any):
            failing += 1
            print(f"❌ [{tc.id}] {tc.name} — missing expected keywords ({ms}ms)")
            print("Draft:", draft_text[:500], "\n")
            continue

        if tc.expect_question:
            # Accept either a literal question OR an info request
            info_markers = (
                "?",
                "order number",
                "order #",
                "email",
                "transaction",
                "txid",
                "logs",
                "details",
                "can you provide",
                "could you share",
                "could you tell me",
                "before we try",
            )


            if not any(marker in draft_text.lower() for marker in info_markers):
                print(f"❌ [{tc.id}] {tc.name} — expected a question or info request ({ms}ms)")
                failing += 1
                continue




        print(f"✅ [{tc.id}] {tc.name} ({ms}ms)")
        # print just a snippet
        print(draft_text[:180].replace("\n", " ") + ("…" if len(draft_text) > 180 else ""), "\n")

    print("=== RESULT ===")
    if failing:
        print(f"❌ {failing} failing test(s)")
        return 1
    print("✅ All tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
