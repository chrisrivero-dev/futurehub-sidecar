"""
Missing Information Inference
Phase 2.2 — text-based inference only
Observation-only (no UI, no copy changes)
"""

from typing import List, Dict, Any
import re


CONFIDENCE_BLOCKING_THRESHOLD = 0.7


def _severity(confidence: float) -> str:
    return "blocking" if confidence >= CONFIDENCE_BLOCKING_THRESHOLD else "non_blocking"


def _item(key: str, severity: str) -> dict:
    return {
        "key": key,
        "reason": "inferred_from_text",
        "evidence": "message_text",
        "severity": severity,
    }


def infer_missing_information(
    *,
    messages: List[str],
    intent: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Infer missing information from message text.
    Never overrides metadata-based detection.
    """

    text = " ".join(messages).lower()
    primary = intent.get("primary")
    confidence = float(intent.get("confidence", 0.0) or 0.0)

    items: list[dict] = []

    # ==================================================
    # DIAGNOSTIC — Phase 2.2 rules
    # ==================================================
    if primary == "diagnostic":
        mentions_status = any(
            k in text
            for k in [
                "miner is on",
                "powered on",
                "powered off",
                "device is on",
                "device is off",
            ]
        )

        mentions_uptime = any(
            k in text
            for k in [
                "rebooted",
                "restarted",
                "power cycled",
                "uptime",
                "yesterday",
            ]
        )

        # Rule D1 — stopped / zero hash
        if any(
            k in text
            for k in [
                "stopped hashing",
                "not hashing",
                "hash rate zero",
            ]
        ):
            if not mentions_status:
                items.append(_item("device_status", _severity(confidence)))

        # Rule D2 — instability / persistence
        if any(
            k in text
            for k in [
                "keeps dropping",
                "drops to zero",
                "fluctuating",
                "restarting",
            ]
        ):
            if not mentions_status:
                items.append(_item("device_status", _severity(confidence)))

            if not mentions_uptime:
                items.append(_item("uptime_or_last_reboot", "non_blocking"))

        # Rule D5 — all info present → infer nothing
        if mentions_status and mentions_uptime and any(
            k in text for k in ["firmware", "version"]
        ):
            items = []

    # ==================================================
    # SETUP — Phase 2.2 rules
    # ==================================================
    if primary in ("setup", "setup_help"):
        mentions_model = "apollo" in text

        mentions_connection_issue = any(
            k in text
            for k in [
                "can't connect",
                "cannot connect",
                "not connecting",
                "dashboard not loading",
                "dashboard won't load",
                "can't access dashboard",
            ]
        )

        mentions_ip_access = bool(
            re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)
        )

        # Rule S1 — missing device model
        if not mentions_model:
            items.append(_item("device_model", _severity(confidence)))

        # Rule S2 — connection type inferred only if problem + no IP hint
        if mentions_connection_issue and not mentions_ip_access:
            items.append(_item("connection_type", _severity(confidence)))

    # ==================================================
    # SHIPPING — Phase 2.2 rules
    # ==================================================
    if primary in ("shipping", "shipping_status"):
        mentions_order = bool(
            re.search(r"(order\s*#|#\w+|fb\d+)", text)
        )

        mentions_lookup = any(
            k in text
            for k in [
                "shipping help",
                "where is my order",
                "order status",
                "tracking",
            ]
        )

        mentions_contact = any(
            k in text
            for k in [
                "can you check",
                "please look up",
                "help me find",
                "check for me",
            ]
        )

        # Rule S1 / S2 — order number required
        if mentions_lookup and not mentions_order:
            items.append(_item("order_number", _severity(confidence)))

        # Rule S3 — email is helpful but non-blocking
        if mentions_lookup and mentions_contact:
            items.append(_item("email", "non_blocking"))

    return {
        "detected": bool(items),
        "confidence": confidence,
        "items": items,
        "summary": {
            "blocking_count": len([i for i in items if i["severity"] == "blocking"]),
            "non_blocking_count": len([i for i in items if i["severity"] == "non_blocking"]),
        },
    }
