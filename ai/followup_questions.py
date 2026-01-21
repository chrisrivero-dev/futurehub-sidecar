# ai/followup_questions.py

from typing import Dict, Any, List

FOLLOWUP_COPY = {
    # SHIPPING
    "order_number": "Can you share your order number so I can look this up?",
    "email": "What email address was used for the order?",
    "order_timing": "When did you place the order?",

    # SETUP
    "connection_type": "Is your Apollo connected via Ethernet or Wi-Fi?",
    "device_model": "Which Apollo model are you setting up?",
    "dashboard_access": "Have you tried accessing the dashboard using the device’s IP address?",

    # DIAGNOSTIC
    "device_status": "Is the miner currently powered on and running?",
    "uptime_or_last_reboot": "When was the last time the device was rebooted?",
    "diagnostic_behavior": "What behavior are you seeing right now (not hashing, dropping hash rate, offline)?",
}


def build_followup_questions(
    *,
    missing_information: Dict[str, Any],
    intent: Dict[str, Any],
    mode: str,
    draft_text: str,
) -> List[Dict[str, str]]:

    followups: List[Dict[str, str]] = []

    items = missing_information.get("items", [])

    print("FOLLOWUP DEBUG — missing items:", items)

    for item in items:
        key = item.get("key")

        if key not in FOLLOWUP_COPY:
            continue

        followups.append({
            "key": key,
            "question": FOLLOWUP_COPY[key],
            "severity": item.get("severity"),
        })

    return followups

