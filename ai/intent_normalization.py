# ai/intent_normalization.py

INTENT_MAP = {
    "shipping_status": {
        "issue_type": "Shipping",
        "tags": ["shipping-delay"],
    },
    "firmware_update": {
        "issue_type": "Firmware",
        "tags": ["firmware-update"],
    },
    "node_sync_issue": {
        "issue_type": "Syncing",
        "tags": ["sync-issue"],
    },
    "setup_help": {
        "issue_type": "Setup",
        "tags": ["setup-help"],
    },
    "warranty_inquiry": {
        "issue_type": "Warranty",
        "tags": ["warranty-check"],
    },
    "rma_request": {
        "issue_type": "Warranty",
        "tags": ["rma-request"],
    },
    "connectivity_issue": {
        "issue_type": "Connectivity",
        "tags": ["connectivity-issue"],
    },
    "unknown_vague": {
        "issue_type": "General",
        "tags": ["general-inquiry"],
    },
}


def normalize_intent(primary: str | None, secondary: str | None = None):
    """
    Guarantees:
    - Always returns a valid Issue Type
    - Never lets 'unknown' leak downstream
    """

    primary = primary or "unknown_vague"
    secondary = secondary or None

    if primary in INTENT_MAP:
        base = INTENT_MAP[primary]
    else:
        base = INTENT_MAP["unknown_vague"]

    tags = list(base["tags"])

    # Optional secondary tagging (NON-DESTRUCTIVE)
    if secondary and secondary in INTENT_MAP:
        for tag in INTENT_MAP[secondary]["tags"]:
            if tag not in tags:
                tags.append(tag)

    return {
        "issue_type": base["issue_type"],
        "tags": tags,
        "normalized_intent": primary if primary in INTENT_MAP else "unknown_vague",
    }
