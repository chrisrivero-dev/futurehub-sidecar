# FutureHub AI Sidecar — API Contract Gaps & Ambiguities

**Purpose**: Identify missing specifications, unclear behaviors, and contract weaknesses before locking v1.0

---

## 🔴 CRITICAL GAPS (Must Fix Before v1.0 Lock)

### 1. **Auto-Send Eligibility Not Returned in Response**

**Problem**: The response schema does NOT include an `auto_send_eligible` field, but the sidecar is supposed to recommend auto-send for safe intents with high confidence.

**Current State**:
```json
"agent_guidance": {
  "requires_review": true,
  "reason": "...",
  "recommendation": "...",
  "suggested_actions": [...]
}
```

**What's Missing**:
```json
"agent_guidance": {
  "requires_review": true,
  "auto_send_eligible": false,  // ❌ MISSING
  "reason": "...",
  "recommendation": "...",
  "suggested_actions": [...]
}
```

**Impact**: Host system cannot know if auto-send is recommended without reverse-engineering the logic.

**Fix Required**: Add `auto_send_eligible` boolean to `agent_guidance` block.

---

### 2. **`conversation_history` Format Unspecified**

**Problem**: Request schema says `conversation_history` is "array or string" but:
- What's the array structure? (Objects? Strings?)
- If string, what's the format?
- What happens if it's empty?

**Current Ambiguity**:
```json
"conversation_history": ???  // array of what? string of what?
```

**Needs Clarification**:
```json
// Option A: Array of message objects
"conversation_history": [
  {"role": "customer", "text": "...", "timestamp": "..."},
  {"role": "agent", "text": "...", "timestamp": "..."}
]

// Option B: String (concatenated)
"conversation_history": "Customer: ... Agent: ..."

// Option C: Empty array allowed
"conversation_history": []
```

**Impact**: Implementers don't know what to send.

---

### 3. **No Error Codes Beyond `invalid_input`**

**Problem**: Only one error code (`invalid_input`) is documented. What about:
- Malformed JSON?
- Too-large payloads?
- Invalid metadata values?
- Internal server errors?

**Missing Error Codes**:
- `malformed_json`
- `payload_too_large`
- `invalid_metadata`
- `internal_error`
- `service_unavailable`

**Impact**: Host system can't handle errors gracefully.

---

### 4. **No Payload Size Limits Specified**

**Problem**: No documented limits on:
- Maximum `latest_message` length
- Maximum `conversation_history` size
- Maximum attachment count
- Total request size

**Risk**: Unbounded input could break the sidecar.

**Needs Documentation**:
```
Maximum Payload Sizes:
- latest_message: 10,000 characters
- conversation_history: 50 messages or 50KB
- attachments: 10 files
- Total request: 1MB
```

---

### 5. **`processing_time_ms` Is Hardcoded to 50**

**Problem**: In `app.py`:
```python
"processing_time_ms": 50,  # Always 50, not measured
```

This is a placeholder, not real timing.

**Options**:
1. Remove it (not yet implemented)
2. Make it real (measure actual processing time)
3. Keep as estimate (rename to `estimated_processing_ms`)

---

## 🟡 MODERATE GAPS (Should Fix for Production)

### 6. **No Versioning Strategy Beyond "1.0"**

**Problem**: The response includes `"version": "1.0"` but:
- What happens when v1.1 is released?
- How does the host system request a specific version?
- Are older versions supported?

**Missing**:
- Version negotiation mechanism (e.g., `Accept-Version: 1.0` header)
- Deprecation policy
- Backwards compatibility guarantees

---

### 7. **`draft.structure` Is Always Populated with Placeholder Text**

**Problem**: The response includes:
```json
"structure": {
  "opening": "Thank you for contacting us.",
  "body": "An agent will review your message and respond shortly.",
  "closing": ""
}
```

But in `app.py`, this is hardcoded and does NOT reflect the actual draft structure from `draft_generator.py`.

**Impact**: The `structure` field is misleading.

**Options**:
1. Remove `structure` (not yet implemented)
2. Parse draft text into opening/body/closing
3. Mark as `"structure": null` until implemented

---

### 8. **Canned Response `timing` Field Unused**

**Problem**: The canned response recommendation includes:
```json
"timing": "after_diagnostic_review"
```

But this is always the same value and never varies.

**Questions**:
- Is `timing` always `"after_diagnostic_review"` for unsafe intents?
- Could it ever be `"immediate"` or `"after_escalation"`?

**Impact**: If it's always the same, it adds no value.

---

### 9. **No Rate Limiting Documented**

**Problem**: No mention of:
- Request rate limits
- Concurrent request limits
- Throttling behavior

**Risk**: Host system could overwhelm the sidecar.

---

### 10. **Ambiguity in "Requires Review" Logic**

**Problem**: In `app.py`:
```python
"requires_review": True,  # Always true (draft gen not implemented)
```

But once draft generation is complete, when is `requires_review` false?

**Needs Clarification**:
```
requires_review = false IF:
  - auto_send_eligible = true
  - confidence >= 85%
  - draft_type = "full"
  
requires_review = true IF:
  - safety_mode = "unsafe"
  - draft_type = "clarification_only" or "escalation"
  - confidence < 85%
```

---

## 🟢 MINOR GAPS (Nice-to-Have for v1.0)

### 11. **No Request ID for Tracing**

**Problem**: Requests and responses have no unique identifier.

**Suggested Addition**:
```json
{
  "request_id": "uuid-1234-5678",
  "timestamp": "..."
}
```

**Benefit**: Debugging and logging.

---

### 12. **No Webhook/Callback Support**

**Problem**: Synchronous only. No async processing option.

**Future Consideration**: Long-running classification or knowledge retrieval might need async mode.

---

### 13. **No Multi-Language Support (English Only)**

**Current**: English-only templates and keyword matching.

**Future**: Should contract specify language detection and multi-language support?

---

### 14. **No Metadata Validation**

**Problem**: The sidecar accepts any metadata structure:
```json
"metadata": {
  "anything": "goes",
  "here": 123
}
```

**Needs**: Documented valid metadata fields and types.

---

### 15. **`classification_reasoning` Is Generic**

**Problem**: Always returns:
```
"Intent detected as {intent} based on keyword analysis"
```

**Could Be More Useful**:
```
"Intent detected as not_hashing based on:
 - Trigger phrase: '0 h/s' (3.0 pts)
 - Strong signal: 'not hashing' (2.0 pts)
 - Attachment present (+2.0 pts)
 Total score: 9.0"
```

---

## 🔵 CONSISTENCY ISSUES

### 16. **Inconsistent Naming Conventions**

- `latest_message` (snake_case)
- `conversation_history` (snake_case)
- BUT metadata keys are inconsistent:
  - `order_number` (snake_case)
  - `product` (no convention specified)

**Recommendation**: Enforce snake_case everywhere.

---

### 17. **Boolean vs. Enum Ambiguity**

- `draft_available` is boolean (true/false)
- But what if draft generation fails? Should it be `null` or an enum?

**Options**:
```json
"draft_available": true | false | "partial" | "failed"
```

---

### 18. **`success` Field Redundancy**

**Problem**: HTTP status code + `success` field both indicate success.

**Question**: Is `success: true` necessary when status is 200 OK?

**Typical Pattern**:
- 200 OK = success (no `success` field needed)
- 4xx/5xx = error (error object present)

---

## 🧪 TESTING GAPS

### 19. **No Test Cases in Contract**

**Missing**: Canonical examples showing:
- Edge cases (empty history, missing customer name)
- Error scenarios (malformed JSON, missing fields)
- Boundary conditions (exactly 85% confidence)

---

### 20. **No Schema Validation Tool**

**Problem**: No JSON Schema or OpenAPI spec to validate requests/responses.

**Recommendation**: Add JSON Schema for automated validation.

---

## 📊 SUMMARY OF GAPS

| Category          | Critical | Moderate | Minor | Total |
| ----------------- | -------- | -------- | ----- | ----- |
| Missing Fields    | 1        | 2        | 1     | 4     |
| Ambiguous Behavior| 2        | 3        | 2     | 7     |
| Missing Limits    | 2        | 1        | 0     | 3     |
| Consistency       | 0        | 0        | 3     | 3     |
| Testing           | 0        | 0        | 2     | 2     |
| **TOTAL**         | **5**    | **6**    | **8** | **19**|

---

## 🎯 RECOMMENDED FIXES FOR v1.0 LOCK

### Must Fix (Blockers)

1. ✅ Add `auto_send_eligible` to `agent_guidance`
2. ✅ Specify `conversation_history` format
3. ✅ Document error codes
4. ✅ Add payload size limits
5. ✅ Fix or remove `processing_time_ms`

### Should Fix (Highly Recommended)

6. ✅ Define versioning strategy
7. ✅ Fix or remove `draft.structure`
8. ✅ Clarify `requires_review` logic
9. ✅ Add request ID for tracing

### Could Fix (Nice-to-Have)

10. ✅ Document rate limits
11. ✅ Validate metadata schema
12. ✅ Enhance `classification_reasoning`

---

**End of Gap Analysis**
