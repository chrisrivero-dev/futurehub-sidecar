# FutureHub AI Sidecar — Current API Contract (v1.0 Draft)

**Status**: In Development (Phase 2 Complete, Phase 3 In Progress)  
**Last Updated**: 2024-01-13  
**Scope**: AI Sidecar Service Only (Not Host System)

---

## Overview

The FutureHub AI Sidecar receives support ticket data, performs intent classification, generates advisory drafts, and returns agent guidance. The sidecar **never sends messages** — it only provides recommendations.

---

## Endpoint

```
POST /api/v1/draft
```

**Purpose**: Generate draft response for a support ticket

---

## Request Schema

### Required Fields

```json
{
  "subject": "string (ticket subject line)",
  "latest_message": "string (most recent customer message)",
  "conversation_history": "array or string (previous messages in ticket)"
}
```

### Optional Fields

```json
{
  "metadata": {
    "order_number": "string (e.g., FBT-2024-1234)",
    "product": "string (e.g., Apollo II, Apollo III, Solo Node)",
    "attachments": ["array of attachment objects or filenames"]
  },
  "customer_name": "string (for personalization)"
}
```

### Example Request

```json
{
  "subject": "Apollo not working",
  "latest_message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
  "conversation_history": [],
  "metadata": {
    "product": "Apollo II",
    "attachments": ["debug.log"]
  },
  "customer_name": "Mark"
}
```

---

## Response Schema

### Success Response (200 OK)

```json
{
  "success": true,
  "draft_available": true,
  "version": "1.0",
  "timestamp": "2024-01-13T10:30:00.000Z",
  "processing_time_ms": 50,
  
  "intent_classification": {
    "primary_intent": "string",
    "secondary_intents": ["array of strings"],
    "confidence": {
      "overall": 0.85,
      "dimensions": {
        "intent_confidence": 0.85,
        "knowledge_coverage": 0.0,
        "draft_quality": 0.0
      },
      "label": "high|medium|low|very_low",
      "ambiguity_detected": false
    },
    "tone_modifier": "neutral|panic|frustration|confusion",
    "safety_mode": "safe|unsafe",
    "device_behavior_detected": true,
    "attempted_actions": ["restart", "firmware_update"],
    "signal_breakdown": {
      "not_hashing": 9.0,
      "sync_delay": 2.0,
      "setup_help": 1.0
    },
    "classification_reasoning": "Intent detected as not_hashing based on keyword analysis"
  },
  
  "draft": {
    "type": "full|clarification_only|escalation",
    "response_text": "string (complete draft message)",
    "structure": {
      "opening": "string",
      "body": "string",
      "closing": "string"
    },
    "quality_metrics": {
      "structure_score": 0.80,
      "source_grounding": 0.0,
      "reasoning_clarity": 0.60,
      "tone_appropriateness": 0.90,
      "hallucination_risk": 0.0,
      "already_tried_avoidance": 1.0
    }
  },
  
  "knowledge_retrieval": {
    "sources_consulted": [],
    "coverage": "none",
    "gaps": ["Knowledge retrieval not yet implemented"]
  },
  
  "agent_guidance": {
    "requires_review": true,
    "reason": "string (why review needed)",
    "recommendation": "string (what agent should do)",
    "suggested_actions": ["array of strings"]
  }
}
```

### Error Response (400 Bad Request)

```json
{
  "success": false,
  "error": {
    "code": "invalid_input",
    "message": "Missing required fields: subject",
    "details": {
      "missing_fields": ["subject"],
      "required_fields": ["subject", "latest_message", "conversation_history"]
    }
  },
  "timestamp": "2024-01-13T10:30:00.000Z"
}
```

---

## Intent Taxonomy

### Available Intents (9 Total)

| Intent               | Description                              | Safety Mode | Auto-Send Eligible |
| -------------------- | ---------------------------------------- | ----------- | ------------------ |
| `shipping_status`    | Order/delivery questions                 | safe        | ✅ Yes              |
| `setup_help`         | Configuration, pool setup                | safe        | ✅ Yes              |
| `general_question`   | Educational, informational               | safe        | ✅ Yes              |
| `warranty_rma`       | Refund, return, RMA requests             | safe        | ✅ Yes              |
| `not_hashing`        | Device not mining (0 H/s)                | unsafe      | ❌ No               |
| `sync_delay`         | Blockchain sync stuck/slow               | unsafe      | ❌ No               |
| `firmware_issue`     | Update failed, UI frozen, bricked device | unsafe      | ❌ No               |
| `performance_issue`  | Restarts, overheating, instability       | unsafe      | ❌ No               |
| `unknown_vague`      | Unclear or insufficient information      | safe        | ❌ No               |

### Safety Classification

- **Safe Intents**: Informational requests with no risk of incorrect troubleshooting
- **Unsafe Intents**: Diagnostic issues requiring data collection before troubleshooting

---

## Draft Types

### 1. `full`
- **When**: Safe intents (`shipping_status`, `setup_help`, `general_question`, `warranty_rma`)
- **What**: Complete response providing information or asking clarifying questions
- **Auto-send eligible**: Yes (confidence ≥ 85%)

### 2. `clarification_only`
- **When**: Unsafe intents OR `unknown_vague`
- **What**: Acknowledges issue, requests diagnostic data (logs, command output)
- **Auto-send eligible**: No

### 3. `escalation`
- **When**: Customer has tried 3+ troubleshooting steps
- **What**: Acknowledges thorough troubleshooting, requests diagnostic data for root cause analysis
- **Auto-send eligible**: No

---

## Confidence Calculation

### Confidence Labels

| Score Range  | Label      | Meaning                           |
| ------------ | ---------- | --------------------------------- |
| ≥ 0.85       | `high`     | Strong match, auto-send eligible  |
| 0.70 - 0.84  | `medium`   | Moderate match, review suggested  |
| 0.50 - 0.69  | `low`      | Weak match, manual review needed  |
| < 0.50       | `very_low` | Unclear intent, clarify with user |

### Intent Scoring System

- **Trigger phrases**: 3.0 points each (e.g., "where is my order", "0 h/s")
- **Strong signals**: 2.0 points each (e.g., "tracking", "not hashing")
- **Weak signals**: 1.0 point each (e.g., "order", "mining")

### Modifiers

- **Device behavior detected**: Boosts technical intents by 15%, reduces informational by 15%
- **Order number present**: +2.0 to `shipping_status`
- **Attachments present**: +2.0 to all unsafe intents
- **Already tried 2+ steps**: +10% to unsafe intents, -15% to `setup_help`

### Ambiguity Detection

If top two intents are within 1.0 point of each other, `ambiguity_detected` = `true` and priority tie-breaking applies:

**Priority Order** (highest to lowest):
1. `warranty_rma`
2. `shipping_status`
3. `firmware_issue`
4. `not_hashing`
5. `sync_delay`
6. `performance_issue`
7. `setup_help`
8. `general_question`
9. `unknown_vague`

---

## Tone Detection

### Detected Tones

- **`neutral`**: Default (no emotional indicators)
- **`panic`**: Urgent language, exclamation marks (≥3), words like "losing money"
- **`frustration`**: "still not working", "again", "multiple times"
- **`confusion`**: "confused", "don't understand", "unclear"

### Tone Handling

If `panic` tone detected, draft includes immediate reassurance:
> "[Customer name], I understand this is urgent and you need help right away."

---

## Quality Metrics

### Structure Score (0.0 - 1.0)
- Has greeting (e.g., "Thanks for reaching out"): +0.33
- Has body (>100 characters): +0.34
- Has closing (e.g., "Agent will respond..."): +0.33

### Source Grounding (0.0 - 1.0)
- **Not yet implemented** (placeholder: 0.0)

### Reasoning Clarity (0.6 - 0.8)
- Draft includes explanation (e.g., "to help", "so we can"): 0.80
- No explanation: 0.60

### Tone Appropriateness (0.7 - 0.9)
- Empathy present (e.g., "understand", "I can see"): 0.90
- No empathy: 0.70

### Hallucination Risk (0.05 - 0.30)
- Contains specific dates/numbers WITHOUT qualifying language: 0.30
- Generic or qualified claims: 0.05

### Already-Tried Avoidance (1.0)
- **Not yet implemented** (placeholder: 1.0)

---

## Canned Response Recommendations

For **unsafe intents only**, the sidecar recommends a canned response category:

```json
"canned_response_suggestion": {
  "category": "Node Not Hashing Troubleshooting",
  "reason": "Intent is not_hashing. Canned response contains step-by-step troubleshooting.",
  "timing": "after_diagnostic_review"
}
```

### Available Categories

| Intent               | Canned Response Category          |
| -------------------- | --------------------------------- |
| `not_hashing`        | Node Not Hashing Troubleshooting  |
| `sync_delay`         | Node Sync Troubleshooting         |
| `firmware_issue`     | Firmware Update Instructions      |
| `performance_issue`  | Performance Diagnostics           |

**Note**: Safe intents do NOT receive canned response recommendations.

---

## Already-Tried Detection

The sidecar detects when customers mention previously attempted troubleshooting:

### Detected Actions

| Action             | Trigger Patterns                                          |
| ------------------ | --------------------------------------------------------- |
| `restart`          | "already tried restarting", "i restarted"                 |
| `firmware_update`  | "already updated firmware", "tried updating"              |
| `pool_change`      | "changed pools", "tried different pool"                   |
| `check_logs`       | "checked logs", "looked at logs"                          |

### Impact

- **2+ actions**: Boosts unsafe intents by 10%, reduces `setup_help` by 15%
- **3+ actions**: Triggers `escalation` draft type

---

## Device Detection

The sidecar extracts device name from `metadata.product`:

| Input String               | Detected Device |
| -------------------------- | --------------- |
| "Apollo III", "Apollo3"    | Apollo III      |
| "Apollo II", "Apollo2"     | Apollo II       |
| "Solo Node"                | Solo Node       |
| Anything else / missing    | Apollo          |

---

## Auto-Send Eligibility Rules

### Criteria (ALL must be true)

1. ✅ Intent is `shipping_status`, `setup_help`, `general_question`, or `warranty_rma`
2. ✅ Confidence ≥ 85%
3. ✅ Draft type is `full`
4. ✅ No attachments present
5. ✅ Safety mode is `safe`

### Disqualifiers (ANY of these = no auto-send)

- ❌ Unsafe intent
- ❌ Confidence < 85%
- ❌ Draft type is `clarification_only` or `escalation`
- ❌ Attachments present
- ❌ Ambiguity detected

**Note**: Auto-send is a **recommendation only**. The host system must still require agent approval.

---

## Health Check Endpoint

```
GET /health
```

### Response (200 OK)

```json
{
  "status": "healthy",
  "version": "1.0",
  "timestamp": "2024-01-13T10:30:00.000Z"
}
```

---

## Guarantees (What the Sidecar Promises)

1. **Deterministic Classification**: Same input always produces same intent
2. **No Silent Actions**: Sidecar never sends messages or takes actions
3. **Fail-Safe Defaults**: On error or ambiguity, defaults to manual review
4. **Template Integrity**: All drafts use frozen templates (no hallucinated steps)
5. **Confidence Honesty**: Low confidence is flagged, not hidden

---

## What's NOT Implemented Yet

- ✅ Knowledge retrieval (`sources_consulted` is empty)
- ✅ Draft quality dimensions (`knowledge_coverage`, `draft_quality` are placeholders)
- ✅ Source grounding metric (always 0.0)
- ✅ Already-tried avoidance metric (always 1.0)

---

## Known Limitations

1. **Language**: English only
2. **Product Scope**: Apollo devices only (Apollo, Apollo II, Apollo III, Solo Node)
3. **Intent Taxonomy**: 9 intents only (not extensible without code changes)
4. **Template-Based**: No generative AI (future enhancement)
5. **No Context Memory**: Each request is stateless

---

## Version History

- **v1.0** (Current): Rule-based intent classification + template-based drafts
- **v2.0** (Future): Knowledge base integration
- **v3.0** (Future): Generative AI drafts with knowledge grounding

---

**End of Current API Contract**
