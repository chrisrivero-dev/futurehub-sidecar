"""
Intent Classification Module
Rule-based, deterministic intent detection for support tickets
"""

print(">>> intent_classifier loaded from:", __file__)


# Intent taxonomy (9 intents)
INTENTS = [
    "shipping_status",
    "setup_help",
    "not_hashing",
    "sync_delay",
    "firmware_issue",
    "firmware_update",
    "purchase_inquiry",
    "performance_issue",
    "warranty_rma",
    "general_question",
    "unknown_vague"
]

# Safety classification
SAFE_INTENTS = [
    "shipping_status",
    "setup_help",
    "firmware_update",
    "purchase_inquiry",  # ✅ SAFE + AUTO-SEND ELIGIBLE
    "general_question",
    "warranty_rma"
]

UNSAFE_INTENTS = [
    "not_hashing",
    "sync_delay",
    "firmware_issue",
    "performance_issue"
]



# Keyword definitions with weights
INTENT_KEYWORDS = {
        "purchase_inquiry": {
        "trigger_phrases": [
            "want to purchase",
            "want to buy",
            "buy another",
            "purchase another",
            "order another",
            "get another node",
            "buy a node",
            "purchase a node",
        ],
        "strong_signals": [
            "purchase",
            "buy",
            "order",
            "pricing",
            "cost",
            "price",
            "availability",
        ],
        "weak_signals": [
            "another",
            "node",
            "unit",
        ],
    },

    "shipping_status": {
        "trigger_phrases": [
            "where is my order",
            "where's my order",
            "purchase_inquiry"
            
            "track my order",
            "shipping status",
            "delivery status",
            "when will it arrive",
            "when will it ship",
            "order hasn't arrived",
            "package hasn't arrived",
            "tracking number"
        ],
        "strong_signals": [
            "shipment", "delivery", "tracking", "shipped",
            "fedex", "ups", "usps", "eta", "estimated delivery",
            "order status"
        ],
        "weak_signals": [
            "order", "package", "waiting", "arrived", "receive"
        ]
    },
    
    "setup_help": {
        "trigger_phrases": [
            "how do i set up",
            "how to set up",
            "how do i configure",
            "first time setup",
            "getting started",
            "can't access web interface",
            "can't connect to apollo.local",
            "pool configuration",
            "how do i connect to pool",
            "setup guide"
        ],
        "strong_signals": [
            "setup", "configure", "configuration", "web interface",
            "apollo.local", "pool settings", "pool url", "worker name",
            "first time", "brand new"
        ],
        "weak_signals": [
            "how do i", "how to", "instructions", "guide", "tutorial"
        ]
    },
    
    "not_hashing": {
        "trigger_phrases": [
            "0 h/s",
            "zero hashrate",
            "not hashing",
            "stopped mining",
            "stopped hashing",
            "no hashrate",
            "hashrate is zero",
            "no shares accepted",
            "shares not submitting",
            "worker not found",
            "not mining"  # Added - very specific
        ],
        "strong_signals": [
            "mining stopped", "no shares",
            "shares rejected", "hashrate dropped", "hashrate zero",
            "can't mine", "won't mine"
        ],
        "weak_signals": [
            "hashrate", "mining", "shares", "h/s"
        ]
    },
    
    "sync_delay": {
        "trigger_phrases": [
            "stuck syncing",
            "stuck at block",
            "sync stuck",
            "not syncing",
            "sync stopped",
            "syncing slowly",
            "sync taking forever",
            "blockchain won't sync",
            "node stuck"
        ],
        "strong_signals": [
            "sync", "syncing", "synchronizing", "blockchain",
            "block height", "downloading blocks", "verification",
            "blocks behind"
        ],
        "weak_signals": [
            "block", "progress", "loading"
        ]
    },
    
    "firmware_issue": {
        "trigger_phrases": [
            "firmware update failed",
            "firmware won't update",
            "ui won't load",
            "web interface won't load",
            "can't access interface",
            "device bricked",
            "screen is black",
            "won't boot",
            "stuck on boot"
        ],
        "strong_signals": [
            "update failed", "ui frozen",
            "interface frozen", "unresponsive", "bricked",
            "won't start", "won't boot"
        ],
        "weak_signals": [
            "update", "interface", "ui", "screen", "load"
        ]
    },
    
    "performance_issue": {
        "trigger_phrases": [
            "keeps restarting",
            "keeps rebooting",
            "keeps crashing",
            "overheating",
            "too hot",
            "fans are loud",
            "fans running full speed",
            "unstable",
            "intermittent"
        ],
        "strong_signals": [
            "restarting", "rebooting", "crashing", "hot",
            "temperature", "fan noise", "loud fan",
            "random restarts", "disconnecting"
        ],
        "weak_signals": [
            "restart", "crash", "fan", "noise", "temperature"
        ]
    },
    
    "warranty_rma": {
        "trigger_phrases": [
            "want a refund",
            "request refund",
            "return policy",
            "warranty claim",
            "rma request",
            "defective unit",
            "doesn't work at all",
            "broken on arrival",
            "dead on arrival",
            "doa"
        ],
        "strong_signals": [
            "refund", "return", "warranty", "rma",
            "defective", "broken", "exchange", "replacement"
        ],
        "weak_signals": [
            "policy", "covered", "guarantee"
        ]
    },
    
    "general_question": {
        "trigger_phrases": [
            "what is",
            "how does",
            "can you explain",
            "what's the difference between",
            "how do i know if",
            "is it normal",
            "should i"
        ],
        "strong_signals": [
            "question about", "wondering", "curious",
            "understand", "explain", "difference", "mean"
        ],
        "weak_signals": [
            "how", "why", "what", "when"
        ]
    }
}
def detect_attempted_actions(text):
    """Detect steps customer has already tried"""
    actions = []

    already_tried_patterns = [
        ("restart", [
            "already tried restarting",
            "already restarted",
            "tried restarting",
            "i restarted",
            "already tried: restart",
            "tried: restart",
        ]),
        ("firmware_update", [
            "already updated firmware",
            "updated firmware",
            "tried updating",
            "firmware update",
            "updating firmware",
            "tried: updating firmware",
        ]),
        ("pool_change", [
            "changed pools",
            "tried different pool",
            "switched pools",
            "changing pools",
            "tried: changing pools",
        ]),
        ("check_logs", [
            "checked logs",
            "looked at logs",
            "reviewed logs",
            "tried: checking logs",
        ]),
    ]

    for action, patterns in already_tried_patterns:
        if any(p in text for p in patterns):
            actions.append(action)

    return actions


def detect_tone(text):
    """Detect emotional tone from message"""
    panic_keywords = ["urgent", "asap", "emergency", "immediately", "losing money"]
    frustration_keywords = ["still not working", "again", "multiple times", "frustrated"]
    confusion_keywords = ["confused", "don't understand", "unclear", "not sure"]

    if any(k in text for k in panic_keywords) or text.count("!") >= 3:
        return "panic"
    if any(k in text for k in frustration_keywords):
        return "frustration"
    if any(k in text for k in confusion_keywords):
        return "confusion"

    return "neutral"


def calculate_max_possible_score(intent):
    """Calculate theoretical max score for an intent"""
    keywords = INTENT_KEYWORDS.get(intent, {})

    max_score = 0.0
    max_score += len(keywords.get("trigger_phrases", [])) * 4.0
    max_score += len(keywords.get("strong_signals", [])) * 2.0
    max_score += len(keywords.get("weak_signals", [])) * 1.0

    return max_score if max_score > 0 else 10.0

# PHASE 1.2 LOCKED — setup_help hard detection
# Do not modify without updating tests
def detect_intent(subject, message, metadata=None):
    """
    Classify intent based on keywords and signals.
    """

    # -----------------------------
    # Normalize input
    # -----------------------------
    subject = (subject or "").strip()
    message = (message or "").strip()
    text = f"{subject} {message}".lower()

    text = (
        text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
    )

    attempted_actions = detect_attempted_actions(text)
    device_behavior_detected = False

    # -----------------------------
    # Initialize scores
    # -----------------------------
    scores = {intent: 0.0 for intent in INTENTS}

    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0.0

        for phrase in keywords.get("trigger_phrases", []):
            if phrase in text:
                score += 4.0

        for word in keywords.get("strong_signals", []):
            if word in text:
                score += 2.0

        for word in keywords.get("weak_signals", []):
            if word in text:
                score += 1.0

        scores[intent] = score

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # -----------------------------
    # Determine primary intent
    # -----------------------------
    primary_intent, max_score = sorted_scores[0]

    if max_score < 2.0:
        primary_intent = "unknown_vague"
        intent_confidence = 0.2
        ambiguity_detected = False
    else:
        intent_confidence = min(
            scores[primary_intent] / calculate_max_possible_score(primary_intent),
            1.0,
        )
        ambiguity_detected = False

    # -----------------------------
    # Post-classification metadata
    # -----------------------------
    tone_modifier = detect_tone(text)
    safety_mode = "unsafe" if primary_intent in UNSAFE_INTENTS else "safe"

    secondary_intents = [
        intent for intent, score in sorted_scores[1:3]
        if score >= 3.0 and intent != primary_intent
    ]

    return {
        "primary_intent": primary_intent,
        "secondary_intents": secondary_intents,
        "confidence": {
            "intent_confidence": round(intent_confidence, 2),
            "ambiguity_detected": ambiguity_detected,
        },
        "tone_modifier": tone_modifier,
        "safety_mode": safety_mode,
        "device_behavior_detected": device_behavior_detected,
        "attempted_actions": attempted_actions,
        "scores": {
            intent: round(score, 1)
            for intent, score in sorted_scores[:5]
        },
    }
