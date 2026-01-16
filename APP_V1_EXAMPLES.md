# app.py v1.0 — Request/Response Examples

---

## Example 1: Valid Request (Shipping Status - Auto-Send Eligible)

### Request
```json
POST /api/v1/draft

{
  "subject": "Where is my order?",
  "latest_message": "Where is my order #FBT-2024-1234? I ordered an Apollo II last week.",
  "conversation_history": [],
  "customer_name": "Sarah",
  "metadata": {
    "order_number": "FBT-2024-1234",
    "product": "Apollo II"
  }
}
```

### Response (200 OK)
```json
{
  "success": true,
  "draft_available": true,
  "version": "1.0",
  "timestamp": "2024-01-13T10:30:15.456Z",
  "processing_time_ms": 42,
  
  "intent_classification": {
    "primary_intent": "shipping_status",
    "secondary_intents": [],
    "confidence": {
      "overall": 0.92,
      "dimensions": {
        "intent_confidence": 0.92,
        "knowledge_coverage": 0.0,
        "draft_quality": 0.0
      },
      "label": "high",
      "ambiguity_detected": false
    },
    "tone_modifier": "neutral",
    "safety_mode": "safe",
    "device_behavior_detected": false,
    "attempted_actions": [],
    "signal_breakdown": {
      "shipping_status": 8.0,
      "setup_help": 1.0,
      "general_question": 0.5
    },
    "classification_reasoning": "Intent detected as shipping_status based on keyword analysis"
  },
  
  "draft": {
    "type": "full",
    "response_text": "Hi Sarah,\n\nI'll need to look up your order details to give you an accurate status. An agent will check your order #FBT-2024-1234 and respond with tracking information within 2 hours.\n\nIn the meantime, typical Apollo shipping timeframes are 3-5 business days from order date.",
    "quality_metrics": {
      "structure_score": 1.0,
      "source_grounding": 0.0,
      "reasoning_clarity": 0.8,
      "tone_appropriateness": 0.9,
      "hallucination_risk": 0.05,
      "already_tried_avoidance": 1.0
    }
  },
  
  "knowledge_retrieval": {
    "sources_consulted": [],
    "coverage": "none",
    "gaps": ["Knowledge retrieval not yet implemented"]
  },
  
  "agent_guidance": {
    "requires_review": false,
    "auto_send_eligible": true,
    "reason": "High-confidence shipping inquiry (shipping_status). Auto-send eligible.",
    "recommendation": "Informational request. Provide accurate information from knowledge base.",
    "suggested_actions": [
      "Look up order in admin system",
      "Provide accurate tracking information",
      "Set realistic delivery expectations"
    ]
  }
}
```

**Key Points**:
- ✅ `auto_send_eligible: true` (intent = shipping_status, confidence ≥ 0.85, no attachments)
- ✅ `requires_review: false` (inverse of auto_send_eligible)
- ✅ Draft uses customer name ("Hi Sarah")
- ✅ Draft references order number (#FBT-2024-1234)
- ✅ Processing time measured (42ms)

---

## Example 2: Valid Request (Diagnostic Issue - Manual Review Required)

### Request
```json
POST /api/v1/draft

{
  "subject": "Apollo not working",
  "latest_message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
  "conversation_history": [],
  "customer_name": "Mark",
  "metadata": {
    "product": "Apollo II",
    "attachments": ["debug.log"]
  }
}
```

### Response (200 OK)
```json
{
  "success": true,
  "draft_available": true,
  "version": "1.0",
  "timestamp": "2024-01-13T10:31:22.789Z",
  "processing_time_ms": 38,
  
  "intent_classification": {
    "primary_intent": "not_hashing",
    "secondary_intents": [],
    "confidence": {
      "overall": 0.95,
      "dimensions": {
        "intent_confidence": 0.95,
        "knowledge_coverage": 0.0,
        "draft_quality": 0.0
      },
      "label": "high",
      "ambiguity_detected": false
    },
    "tone_modifier": "neutral",
    "safety_mode": "unsafe",
    "device_behavior_detected": true,
    "attempted_actions": ["restart"],
    "signal_breakdown": {
      "not_hashing": 11.0,
      "sync_delay": 2.0,
      "setup_help": 1.0
    },
    "classification_reasoning": "Intent detected as not_hashing based on keyword analysis"
  },
  
  "draft": {
    "type": "clarification_only",
    "response_text": "Thanks for reaching out, Mark. I understand your Apollo II isn't hashing — that's definitely something we need to resolve.\n\nI see you've already tried restarting — good troubleshooting.\n\nTo help diagnose this, can you provide:\n\n• Your debug.log file\n  (Settings → Logs → Download)\n  \n• Output from: bitcoin-cli getblockchaininfo\n\nAn agent will review these details and provide specific troubleshooting steps within 4 hours.",
    "quality_metrics": {
      "structure_score": 1.0,
      "source_grounding": 0.0,
      "reasoning_clarity": 0.8,
      "tone_appropriateness": 0.9,
      "hallucination_risk": 0.05,
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
    "auto_send_eligible": false,
    "reason": "Diagnostic issue detected (not_hashing). Request data before troubleshooting.",
    "recommendation": "Diagnostic issue detected (not_hashing). Request data before troubleshooting.",
    "suggested_actions": [
      "Request debug.log and getblockchaininfo output",
      "Review logs for error patterns",
      "Consider: Node Not Hashing Troubleshooting canned response"
    ],
    "canned_response_suggestion": {
      "category": "Node Not Hashing Troubleshooting",
      "reason": "Intent is not_hashing. Canned response contains step-by-step troubleshooting.",
      "timing": "after_diagnostic_review"
    }
  }
}
```

**Key Points**:
- ❌ `auto_send_eligible: false` (unsafe intent)
- ✅ `requires_review: true`
- ✅ Draft type: `clarification_only` (data request, not troubleshooting)
- ✅ Acknowledges already-tried steps ("I see you've already tried restarting")
- ✅ Includes canned response suggestion

---

## Example 3: Valid Request (Conversation History)

### Request
```json
POST /api/v1/draft

{
  "subject": "Sync stuck",
  "latest_message": "It's still stuck at the same block number.",
  "conversation_history": [
    {
      "role": "customer",
      "text": "My node is stuck at block 800,000 for 2 days.",
      "timestamp": "2024-01-10T10:00:00Z"
    },
    {
      "role": "agent",
      "text": "Can you run bitcoin-cli getblockchaininfo and share the output?",
      "timestamp": "2024-01-10T11:00:00Z"
    },
    {
      "role": "customer",
      "text": "It's still stuck at the same block number.",
      "timestamp": "2024-01-10T12:00:00Z"
    }
  ],
  "customer_name": "Taylor",
  "metadata": {
    "product": "Apollo II"
  }
}
```

### Response (200 OK)
```json
{
  "success": true,
  "draft_available": true,
  "version": "1.0",
  "timestamp": "2024-01-13T10:32:45.123Z",
  "processing_time_ms": 35,
  
  "intent_classification": {
    "primary_intent": "sync_delay",
    "secondary_intents": [],
    "confidence": {
      "overall": 0.88,
      "dimensions": {
        "intent_confidence": 0.88,
        "knowledge_coverage": 0.0,
        "draft_quality": 0.0
      },
      "label": "high",
      "ambiguity_detected": false
    },
    "tone_modifier": "neutral",
    "safety_mode": "unsafe",
    "device_behavior_detected": true,
    "attempted_actions": [],
    "signal_breakdown": {
      "sync_delay": 6.0,
      "not_hashing": 2.0
    },
    "classification_reasoning": "Intent detected as sync_delay based on keyword analysis"
  },
  
  "draft": {
    "type": "clarification_only",
    "response_text": "Thanks for reaching out, Taylor. I understand your Apollo II is having sync issues — that's definitely something we need to resolve.\n\nTo confirm progress is happening, can you run:\n\n• bitcoin-cli getblockchaininfo\n\nAnd let me know what block number you see?\n\nAn agent will review these details and provide specific troubleshooting steps within 4 hours.",
    "quality_metrics": {
      "structure_score": 1.0,
      "source_grounding": 0.0,
      "reasoning_clarity": 0.8,
      "tone_appropriateness": 0.9,
      "hallucination_risk": 0.05,
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
    "auto_send_eligible": false,
    "reason": "Diagnostic issue detected (sync_delay). Request data before troubleshooting.",
    "recommendation": "Diagnostic issue detected (sync_delay). Request data before troubleshooting.",
    "suggested_actions": [
      "Request getblockchaininfo output",
      "Check if blocks are incrementing",
      "Consider: Node Sync Troubleshooting canned response"
    ],
    "canned_response_suggestion": {
      "category": "Node Sync Troubleshooting",
      "reason": "Intent is sync_delay. Canned response contains sync troubleshooting steps.",
      "timing": "after_diagnostic_review"
    }
  }
}
```

**Key Points**:
- ✅ Conversation history with 3 messages accepted
- ✅ Draft generated based on latest message
- ❌ `auto_send_eligible: false` (unsafe intent)

---

## Example 4: Error Response (Missing Required Field)

### Request
```json
POST /api/v1/draft

{
  "subject": "Help",
  "latest_message": "My Apollo isn't working."
}
```

### Response (400 Bad Request)
```json
{
  "success": false,
  "error": {
    "code": "invalid_input",
    "message": "Missing or invalid required fields: conversation_history",
    "details": {
      "missing_fields": ["conversation_history"],
      "required_fields": ["subject", "latest_message", "conversation_history"]
    }
  },
  "timestamp": "2024-01-13T10:33:10.456Z"
}
```

---

## Example 5: Error Response (Malformed JSON)

### Request
```
POST /api/v1/draft

{
  "subject": "Help",
  "latest_message": "My Apollo isn't working."
  // Missing closing brace
```

### Response (400 Bad Request)
```json
{
  "success": false,
  "error": {
    "code": "malformed_json",
    "message": "Request body must be valid JSON"
  },
  "timestamp": "2024-01-13T10:34:22.789Z"
}
```

---

## Example 6: Error Response (Payload Too Large)

### Request
```json
POST /api/v1/draft

{
  "subject": "This is a very long subject line that exceeds the 500 character limit...",
  "latest_message": "My Apollo isn't working.",
  "conversation_history": []
}
```

### Response (400 Bad Request)
```json
{
  "success": false,
  "error": {
    "code": "payload_too_large",
    "message": "Field 'subject' exceeds maximum length of 500 characters",
    "details": {
      "field": "subject",
      "max_length": 500
    }
  },
  "timestamp": "2024-01-13T10:35:45.123Z"
}
```

---

## Example 7: Error Response (Invalid Conversation History Format)

### Request
```json
POST /api/v1/draft

{
  "subject": "Help",
  "latest_message": "My Apollo isn't working.",
  "conversation_history": [
    {
      "role": "admin",
      "text": "Invalid role"
    }
  ]
}
```

### Response (400 Bad Request)
```json
{
  "success": false,
  "error": {
    "code": "invalid_input",
    "message": "Message at index 0 must have 'role' field with value 'customer' or 'agent'",
    "details": {
      "field": "conversation_history",
      "message_index": 0
    }
  },
  "timestamp": "2024-01-13T10:36:12.456Z"
}
```

---

## Example 8: Valid Request (Empty Conversation History)

### Request
```json
POST /api/v1/draft

{
  "subject": "Setup question",
  "latest_message": "Just got my Apollo III. How do I set it up?",
  "conversation_history": [],
  "customer_name": "Alex",
  "metadata": {
    "product": "Apollo III"
  }
}
```

### Response (200 OK)
```json
{
  "success": true,
  "draft_available": true,
  "version": "1.0",
  "timestamp": "2024-01-13T10:37:30.789Z",
  "processing_time_ms": 40,
  
  "intent_classification": {
    "primary_intent": "setup_help",
    "secondary_intents": [],
    "confidence": {
      "overall": 0.90,
      "dimensions": {
        "intent_confidence": 0.90,
        "knowledge_coverage": 0.0,
        "draft_quality": 0.0
      },
      "label": "high",
      "ambiguity_detected": false
    },
    "tone_modifier": "neutral",
    "safety_mode": "safe",
    "device_behavior_detected": false,
    "attempted_actions": [],
    "signal_breakdown": {
      "setup_help": 6.0,
      "general_question": 2.0
    },
    "classification_reasoning": "Intent detected as setup_help based on keyword analysis"
  },
  
  "draft": {
    "type": "full",
    "response_text": "Thanks for reaching out, Alex.\n\nFor setting up your Apollo III, I'll need to know a bit more about what you're trying to configure:\n\n• Are you setting up for solo mining or pool mining?\n• Do you have a specific pool in mind, or need recommendations?\n\nOnce I know this, I can provide the exact steps for your setup.",
    "quality_metrics": {
      "structure_score": 1.0,
      "source_grounding": 0.0,
      "reasoning_clarity": 0.8,
      "tone_appropriateness": 0.9,
      "hallucination_risk": 0.05,
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
    "auto_send_eligible": false,
    "reason": "Intent is setup_help but confidence is below threshold. Manual review recommended.",
    "recommendation": "Informational request. Provide accurate information from knowledge base.",
    "suggested_actions": [
      "Provide step-by-step setup instructions",
      "Confirm device is brand new",
      "Reference setup documentation"
    ]
  }
}
```

**Key Points**:
- ✅ Empty `conversation_history: []` accepted (first message in ticket)
- ❌ `auto_send_eligible: false` (intent is NOT shipping_status)
- ✅ Draft type: `full` (safe intent)

---

**End of Examples**
