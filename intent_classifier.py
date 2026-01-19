"""
Intent Classification Module
Rule-based, deterministic intent detection for support tickets
"""

# Intent taxonomy (9 intents)
INTENTS = [
    "shipping_status",
    "setup_help",
    "not_hashing",
    "sync_delay",
    "firmware_issue",
    "firmware_update",
    "performance_issue",
    "warranty_rma",
    "general_question",
    "unknown_vague"
]

# Safety classification
SAFE_INTENTS = [
    "shipping_status",
    "setup_help",
    "firmware_update",   # ✅ SAFE + AUTO-SEND ELIGIBLE
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
    "shipping_status": {
        "trigger_phrases": [
            "where is my order",
            "where's my order", 
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

# PHASE 1.2 LOCKED — setup_help hard detection
# Do not modify without updating tests

def detect_intent(subject, message, metadata=None):
    """
    Classify intent based on keywords and signals.

    Args:
        subject: Ticket subject line
        message: Latest customer message
        metadata: Optional metadata dict

    Returns:
        dict with intent classification results
    """
    # Combine subject and message for analysis (None-safe)
    text = f"{(subject or '').strip()} {(message or '').strip()}".lower()

    # -------------------------------------------------
    # PHASE 1.2 — setup_help hard detection (LOCKED)
    # -------------------------------------------------
    # Normalize smart quotes and apostrophes (U+2019 etc.)
    text = (
        text.replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
    )

    setup_help_phrases = [
        "apollo.local",
        "futurebit.local",
        "doesn't load",
        "doesnt load",
        "won't load",
        "wont load",
        "can't access",
        "cannot access",
        "dashboard won't load",
        "dashboard doesnt load",
        "dashboard doesn't load",
    ]

    if any(phrase in text for phrase in setup_help_phrases):
        return {
            "primary_intent": "setup_help",
            "secondary_intents": [],
            "confidence": {
                "intent_confidence": 0.90,
                "ambiguity_detected": False,
            },
            "tone_modifier": "neutral",
            "safety_mode": "safe",
            "device_behavior_detected": False,
            "attempted_actions": [],
            "scores": {
                "setup_help": 5,
                "shipping_status": 0,
                "not_hashing": 0,
                "sync_delay": 0,
                "general_question": 0,
            },
        }

    # Initialize scores
    scores = {intent: 0.0 for intent in INTENTS}

    # Check for device behavior keywords (overrides informational intents)
    device_behavior_keywords = [
        "0 h/s", "not hashing", "won't load", "won't boot",
        "crashing", "not working", "stopped", "stuck"
    ]
    device_behavior_detected = any(kw in text for kw in device_behavior_keywords)

    # Score each intent
    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0.0

        # Trigger phrases (3.0 points each)
        for phrase in keywords.get("trigger_phrases", []):
            if phrase in text:
                score += 3.0

        # Strong signals (2.0 points each)
        for signal in keywords.get("strong_signals", []):
            if signal in text:
                score += 2.0

        # Weak signals (1.0 point each)
        for signal in keywords.get("weak_signals", []):
            if signal in text:
                score += 1.0

        scores[intent] = score

    # Apply device behavior override
    if device_behavior_detected:
        # Boost technical intents
        for intent in UNSAFE_INTENTS:
            scores[intent] *= 1.15
        # Reduce informational intents
        for intent in ["general_question", "shipping_status"]:
            scores[intent] *= 0.85

    # Check for order number (boosts shipping_status)
    if metadata and metadata.get("order_number"):
        scores["shipping_status"] += 2.0

    # Check for attachments (boosts diagnostic intents)
    if metadata and metadata.get("attachments"):
        for intent in UNSAFE_INTENTS:
            scores[intent] += 2.0

    # Detect already-tried steps
    attempted_actions = detect_attempted_actions(text)
    if len(attempted_actions) >= 2:
        # Boost diagnostic intents
        for intent in UNSAFE_INTENTS:
            scores[intent] *= 1.10
        # Reduce setup_help
        scores["setup_help"] *= 0.85

    # Find primary intent
    max_score = max(scores.values())
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # If max score too low, force unknown_vague
    if max_score < 3.0:
        primary_intent = "unknown_vague"
        intent_confidence = max_score / 10.0  # Low confidence
        ambiguity_detected = False
    else:
        # Check for ambiguity (multiple intents close together)
        top_two_diff = sorted_scores[0][1] - sorted_scores[1][1]

        # Define intent priority for tie-breaking
        INTENT_PRIORITY = [
            "warranty_rma",
            "shipping_status",
            "firmware_issue",
            "not_hashing",
            "sync_delay",
            "performance_issue",
            "setup_help",
            "general_question",
            "unknown_vague"
        ]

        # If tied or very close, use priority order
        if top_two_diff < 1.0:
            top_score = sorted_scores[0][1]
            tied_intents = [
                i for i, s in sorted_scores
                if abs(s - top_score) < 1.0
            ]

            primary_intent = None
            for pi in INTENT_PRIORITY:
                if pi in tied_intents:
                    primary_intent = pi
                    break
            if primary_intent is None:
                primary_intent = sorted_scores[0][0]

            intent_confidence = min(
                scores[primary_intent] / calculate_max_possible_score(primary_intent),
                1.0
            )
            ambiguity_detected = len(tied_intents) > 1
        else:
            primary_intent = sorted_scores[0][0]
            intent_confidence = min(
                scores[primary_intent] / calculate_max_possible_score(primary_intent),
                1.0
            )
            ambiguity_detected = False

    # Detect tone modifier
    tone_modifier = detect_tone(text)

    # Determine safety mode
    safety_mode = "unsafe" if primary_intent in UNSAFE_INTENTS else "safe"

    # Build secondary intents (other high-scoring intents)
    secondary_intents = [
        i for i, s in sorted_scores[1:3]
        if s >= 3.0 and i != primary_intent
    ]

    return {
        "primary_intent": primary_intent,
        "secondary_intents": secondary_intents,
        "confidence": {
            "intent_confidence": round(intent_confidence, 2),
            "ambiguity_detected": ambiguity_detected
        },
        "tone_modifier": tone_modifier,
        "safety_mode": safety_mode,
        "device_behavior_detected": device_behavior_detected,
        "attempted_actions": attempted_actions,
        "scores": {k: round(v, 1) for k, v in sorted_scores[:5]}
    }


def detect_attempted_actions(text):
    """Detect steps customer has already tried"""
    actions = []
    
    already_tried_patterns = [
        ("restart", ["already tried restarting", "already restarted", "tried restarting", "i restarted", "already tried: restart", "tried: restart"]),
        ("firmware_update", ["already updated firmware", "updated firmware", "tried updating", "firmware update", "updating firmware", "tried: updating firmware"]),
        ("pool_change", ["changed pools", "tried different pool", "switched pools", "changing pools", "tried: changing pools"]),
        ("check_logs", ["checked logs", "looked at logs", "reviewed logs", "tried: checking logs"])
    ]
    
    for action, patterns in already_tried_patterns:
        if any(pattern in text for pattern in patterns):
            actions.append(action)
    
    return actions


def detect_tone(text):
    """Detect emotional tone from message"""
    # Panic indicators
    panic_keywords = ["urgent", "asap", "emergency", "immediately", "losing money"]
    if any(kw in text for kw in panic_keywords) or text.count("!") >= 3:
        return "panic"
    
    # Frustration indicators
    frustration_keywords = ["still not working", "again", "multiple times", "frustrated"]
    if any(kw in text for kw in frustration_keywords):
        return "frustration"
    
    # Confusion indicators
    confusion_keywords = ["confused", "don't understand", "unclear", "not sure"]
    if any(kw in text for kw in confusion_keywords):
        return "confusion"
    
    return "neutral"


def calculate_max_possible_score(intent):
    """Calculate theoretical max score for an intent"""
    keywords = INTENT_KEYWORDS.get(intent, {})
    
    max_score = 0
    max_score += len(keywords.get("trigger_phrases", [])) * 3.0
    max_score += len(keywords.get("strong_signals", [])) * 2.0
    max_score += len(keywords.get("weak_signals", [])) * 1.0
    
    # Add typical metadata bonuses
    max_score += 4.0  # Attachments, order numbers, etc.
    
    return max_score if max_score > 0 else 15.0  # Default if no keywords
