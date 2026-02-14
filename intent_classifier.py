"""
Intent Classification Module
Rule-based, deterministic intent detection for support tickets
"""

print(">>> intent_classifier loaded from:", __file__)


# Intent taxonomy
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
    "dashboard_issue",
    "factory_reset",
    "sync_issue",
    "general_question",
    "unknown_vague",
]

# Safety classification
SAFE_INTENTS = [
    "shipping_status",
    "setup_help",
    "firmware_update",
    "purchase_inquiry",
    "general_question",
    "warranty_rma",
    "factory_reset",
    "dashboard_issue",
]

UNSAFE_INTENTS = [
    "not_hashing",
    "sync_delay",
    "sync_issue",
    "firmware_issue",
    "performance_issue",
]


# ==========================================================
# PART 1 — Deterministic hard-map rules (run FIRST)
# Each entry: intent -> list of phrases that force that intent
# ==========================================================

HARD_MAP_RULES = {
    "shipping_status": [
        "where is my order",
        "tracking says delivered",
        "never received",
        "shipping time",
        "how long does shipping take",
        "delivery problem",
        "missing package",
    ],
    "firmware_update": [
        "update firmware",
        "firmware update",
        "flash firmware",
        "upload firmware",
    ],
    "not_hashing": [
        "not hashing",
        "no hashrate",
        "hashrate dropped",
        "won't hash",
    ],
    "factory_reset": [
        "factory reset",
        "reset my unit",
        "restore default",
    ],
    "dashboard_issue": [
        "dashboard not load",
        "dashboard won't load",
        "cannot access dashboard",
    ],
    "sync_issue": [
        "node not sync",
        "not syncing",
        "sync stuck",
    ],
    "warranty_rma": [
        "refund",
        "return",
        "replacement",
        "warranty coverage",
        "secondhand warranty",
    ],
    "performance_issue": [
        "fan loud",
        "overheating",
        "temperature high",
    ],
}


# ==========================================================
# Canonical intent name mapping (normalize before return)
# ==========================================================

CANONICAL_INTENT_MAP = {
    "firmware_update_info": "firmware_update",
    "sync_issue": "sync_delay",
    "factory_reset_info": "factory_reset",
}


# Keyword definitions with weights (used for scoring after hard-map)
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
            "purchase", "buy", "order", "pricing",
            "cost", "price", "availability",
        ],
        "weak_signals": [
            "another", "node", "unit",
        ],
    },
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
            "tracking number",
            "tracking says delivered",
            "never received",
            "shipping time",
            "how long does shipping take",
            "delivery problem",
            "missing package",
        ],
        "strong_signals": [
            "shipment", "delivery", "tracking", "shipped",
            "fedex", "ups", "usps", "eta", "estimated delivery",
            "order status",
        ],
        "weak_signals": [
            "order", "package", "waiting", "arrived", "receive",
        ],
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
            "setup guide",
        ],
        "strong_signals": [
            "setup", "configure", "configuration", "web interface",
            "apollo.local", "pool settings", "pool url", "worker name",
            "first time", "brand new",
        ],
        "weak_signals": [
            "how do i", "how to", "instructions", "guide", "tutorial",
        ],
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
            "not mining",
            "hashrate dropped",
            "won't hash",
        ],
        "strong_signals": [
            "mining stopped", "no shares",
            "shares rejected", "hashrate dropped", "hashrate zero",
            "can't mine", "won't mine",
        ],
        "weak_signals": [
            "hashrate", "mining", "shares", "h/s",
        ],
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
            "node stuck",
            "node not sync",
        ],
        "strong_signals": [
            "sync", "syncing", "synchronizing", "blockchain",
            "block height", "downloading blocks", "verification",
            "blocks behind",
        ],
        "weak_signals": [
            "block", "progress", "loading",
        ],
    },
    "sync_issue": {
        "trigger_phrases": [
            "node not sync",
            "not syncing",
            "sync stuck",
        ],
        "strong_signals": [
            "sync", "syncing", "synchronizing", "blockchain",
        ],
        "weak_signals": [
            "block", "progress",
        ],
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
            "stuck on boot",
        ],
        "strong_signals": [
            "update failed", "ui frozen",
            "interface frozen", "unresponsive", "bricked",
            "won't start", "won't boot",
        ],
        "weak_signals": [
            "update", "interface", "ui", "screen", "load",
        ],
    },
    "firmware_update": {
        "trigger_phrases": [
            "update firmware",
            "firmware update",
            "flash firmware",
            "upload firmware",
            "how to update firmware",
            "firmware upgrade",
        ],
        "strong_signals": [
            "firmware", "update", "flash", "upgrade",
        ],
        "weak_signals": [
            "version", "latest",
        ],
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
            "intermittent",
            "fan loud",
            "temperature high",
        ],
        "strong_signals": [
            "restarting", "rebooting", "crashing", "hot",
            "temperature", "fan noise", "loud fan",
            "random restarts", "disconnecting",
        ],
        "weak_signals": [
            "restart", "crash", "fan", "noise", "temperature",
        ],
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
            "doa",
            "warranty coverage",
            "secondhand warranty",
        ],
        "strong_signals": [
            "refund", "return", "warranty", "rma",
            "defective", "broken", "exchange", "replacement",
        ],
        "weak_signals": [
            "policy", "covered", "guarantee",
        ],
    },
    "factory_reset": {
        "trigger_phrases": [
            "factory reset",
            "reset my unit",
            "restore default",
            "reset to factory",
            "hard reset",
        ],
        "strong_signals": [
            "factory", "reset", "restore", "default",
        ],
        "weak_signals": [
            "wipe", "clean",
        ],
    },
    "dashboard_issue": {
        "trigger_phrases": [
            "dashboard not load",
            "dashboard won't load",
            "cannot access dashboard",
            "dashboard not working",
            "dashboard blank",
        ],
        "strong_signals": [
            "dashboard", "web ui", "control panel",
        ],
        "weak_signals": [
            "page", "browser",
        ],
    },
    "general_question": {
        "trigger_phrases": [
            "what is",
            "how does",
            "can you explain",
            "what's the difference between",
            "how do i know if",
            "is it normal",
            "should i",
        ],
        "strong_signals": [
            "question about", "wondering", "curious",
            "understand", "explain", "difference", "mean",
        ],
        "weak_signals": [
            "how", "why", "what", "when",
        ],
    },
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


def _check_hard_map(text):
    """
    Run deterministic hard-map rules BEFORE any scoring.
    Returns list of all matched intents (may be 0, 1, or multiple).
    """
    matched = []
    for intent, phrases in HARD_MAP_RULES.items():
        for phrase in phrases:
            if phrase in text:
                matched.append(intent)
                break  # one phrase per intent is enough
    return matched


def _compute_keyword_scores(text):
    """Compute weighted keyword scores for all intents."""
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

    return scores


# ==========================================================
# PART 2 — Structured Confidence Scoring
# ==========================================================

def _compute_confidence(
    primary_intent,
    hard_matched,
    scores,
    secondary_intents,
    ambiguity_detected,
    safety_mode,
):
    """
    Compute confidence using weighted structured components:
      base_intent_match_score
      * keyword_density_score
      * ambiguity_penalty
      * multi_intent_penalty
      * safety_penalty

    Rules:
      - Single clear deterministic match -> minimum 0.85 base
      - Multi-question -> subtract 0.15
      - Ambiguous language -> subtract 0.20
      - Unknown intent -> cap at 0.40 maximum
      - Safety_mode unsafe -> cap at 0.60 maximum
    """
    if primary_intent == "unknown_vague":
        return min(0.40, 0.20)

    # Base score: hard-matched deterministic = 0.85 minimum
    if hard_matched:
        base = 0.90
    else:
        # Score-based: scale raw score into 0.50-0.85 range
        raw = scores.get(primary_intent, 0.0)
        if raw >= 8.0:
            base = 0.85
        elif raw >= 6.0:
            base = 0.78
        elif raw >= 4.0:
            base = 0.70
        elif raw >= 2.0:
            base = 0.60
        else:
            base = 0.50

    confidence = base

    # Multi-intent penalty
    if len(secondary_intents) > 0:
        confidence -= 0.15

    # Ambiguity penalty
    if ambiguity_detected:
        confidence -= 0.20

    # Safety cap
    if safety_mode == "unsafe":
        confidence = min(confidence, 0.60)

    # Clamp
    confidence = max(0.10, min(1.0, confidence))

    return round(confidence, 2)


def detect_intent(subject, message, metadata=None):
    """
    Classify intent based on keywords and signals.
    Hard-map rules run FIRST (deterministic).
    - Exactly 1 hard match → short-circuit with 0.90 confidence
    - Multiple hard matches → ambiguity, fall through to scoring, cap 0.75
    - No hard match → keyword scoring fallback
    """

    # -----------------------------
    # Normalize input
    # -----------------------------
    subject = (subject or "").strip()
    message = (message or "").strip()
    text = f"{subject} {message}".lower()

    text = (
        text.replace("\u2018", "'")
            .replace("\u2019", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
    )

    attempted_actions = detect_attempted_actions(text)
    device_behavior_detected = False
    tone_modifier = detect_tone(text)

    # -----------------------------
    # STEP 1: Hard-map rules (deterministic, runs FIRST)
    # -----------------------------
    hard_matches = _check_hard_map(text)

    # -----------------------------
    # SINGLE hard match → short-circuit (skip scoring entirely)
    # -----------------------------
    if len(hard_matches) == 1:
        primary_intent = CANONICAL_INTENT_MAP.get(hard_matches[0], hard_matches[0])
        safety_mode = "unsafe" if primary_intent in UNSAFE_INTENTS else "safe"

        return {
            "primary_intent": primary_intent,
            "secondary_intents": [],
            "confidence": {
                "intent_confidence": 0.90,
                "ambiguity_detected": False,
            },
            "tone_modifier": tone_modifier,
            "safety_mode": safety_mode,
            "device_behavior_detected": device_behavior_detected,
            "attempted_actions": attempted_actions,
            "scores": {primary_intent: 20.0},
        }

    # -----------------------------
    # MULTIPLE hard matches → ambiguity, fall through to scoring
    # -----------------------------
    multi_hard = len(hard_matches) > 1

    # -----------------------------
    # STEP 2: Keyword scoring
    # -----------------------------
    scores = _compute_keyword_scores(text)

    # Boost all hard-matched intents so they rank high
    for hi in hard_matches:
        scores[hi] = max(scores[hi], 20.0)

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # -----------------------------
    # Determine primary intent
    # -----------------------------
    if hard_matches:
        primary_intent = hard_matches[0]
    else:
        primary_intent, max_score = sorted_scores[0]
        if max_score < 2.0:
            primary_intent = "unknown_vague"

    # -----------------------------
    # Detect secondary intents and ambiguity
    # -----------------------------
    secondary_intents = [
        intent for intent, score in sorted_scores[1:3]
        if score >= 3.0 and intent != primary_intent
    ]

    if multi_hard:
        # Multiple hard matches = definite ambiguity
        ambiguity_detected = True
        secondary_intents = [hi for hi in hard_matches[1:] if hi != primary_intent]
    elif len(sorted_scores) >= 2:
        top_score = sorted_scores[0][1]
        runner_score = sorted_scores[1][1]
        ambiguity_detected = (
            top_score > 0
            and runner_score > 0
            and (runner_score / top_score) >= 0.75
            and sorted_scores[0][0] != sorted_scores[1][0]
        )
    else:
        ambiguity_detected = False

    # -----------------------------
    # Post-classification metadata
    # -----------------------------
    # Canonicalize intent name
    primary_intent = CANONICAL_INTENT_MAP.get(primary_intent, primary_intent)
    safety_mode = "unsafe" if primary_intent in UNSAFE_INTENTS else "safe"

    # -----------------------------
    # Structured confidence scoring
    # -----------------------------
    intent_confidence = _compute_confidence(
        primary_intent=primary_intent,
        hard_matched=len(hard_matches) > 0,
        scores=scores,
        secondary_intents=secondary_intents,
        ambiguity_detected=ambiguity_detected,
        safety_mode=safety_mode,
    )

    # Multi-hard-match: cap confidence at 0.75
    if multi_hard:
        intent_confidence = min(intent_confidence, 0.75)

    return {
        "primary_intent": primary_intent,
        "secondary_intents": secondary_intents,
        "confidence": {
            "intent_confidence": intent_confidence,
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
