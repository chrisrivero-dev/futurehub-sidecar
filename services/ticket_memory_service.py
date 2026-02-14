def log_ticket_memory(ticket_data, analysis_data):
    # insert structured row
import json
import os
from datetime import datetime

MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "memory",
    "ticket_events.jsonl"
)


def log_ticket_memory(ticket_data: dict, analysis_data: dict):
    """
    Append structured ticket intelligence event to JSONL memory file.
    """

    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "ticket_id": ticket_data.get("ticket_id"),
        "subject": ticket_data.get("subject"),
        "customer_name": ticket_data.get("customer_name"),

        "intent_primary": analysis_data.get("intent"),
        "confidence": analysis_data.get("confidence"),
        "risk_level": analysis_data.get("risk_level"),
        "draft_outcome": analysis_data.get("draft_outcome"),
        "recommended_action": analysis_data.get("recommended_action"),

        "auto_send_eligible": analysis_data.get("auto_send_eligible"),
        "auto_send_used": analysis_data.get("auto_send_used", False),

        "message_length": len(ticket_data.get("latest_message", "")),
    }

    with open(MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
