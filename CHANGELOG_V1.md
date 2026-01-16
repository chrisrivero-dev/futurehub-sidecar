# v1.0 Contract Lock — Changes Summary

**Status**: 🔒 Phase 3.1 Complete  
**Date**: 2025-01-13  

---

## Critical Blockers Fixed (5/5)

### 1. ✅ Added `auto_send_eligible` Field

**Location**: `agent_guidance` block

**Before**:
```json
"agent_guidance": {
  "requires_review": true,
  "reason": "...",
  "recommendation": "...",
  "suggested_actions": [...]
}
```

**After (v1.0)**:
```json
"agent_guidance": {
  "requires_review": true,
  "auto_send_eligible": false,  // ⭐ NEW
  "reason": "...",
  "recommendation": "...",
  "suggested_actions": [...]
}
```

**Rules**:
- `auto_send_eligible: true` ONLY if:
  - Intent is `shipping_status` (ONLY this intent)
  - Confidence ≥ 85%
  - Draft type is `full`
  - No attachments
  - Safety mode is `safe`
  - No ambiguity detected
- Otherwise: `auto_send_eligible: false`

**Impact**: Host system can now directly check auto-send recommendation without reverse-engineering logic.

---

### 2. ✅ Formalized `conversation_history` Schema

**Before**: "array or string" (ambiguous)

**After (v1.0)**:
```json
"conversation_history": [
  {
    "role": "customer|agent",
    "text": "string (max 10,000 chars)",
    "timestamp": "ISO 8601 string (optional)"
  }
]
```

**Rules**:
- Array of message objects
- `role` must be `"customer"` or `"agent"`
- Chronological order (oldest first)
- Maximum 50 messages
- Each message max 10,000 characters
- Empty array `[]` is valid (first message)

**Impact**: Clear specification for implementers.

---

### 3. ✅ Complete Error Code List

**Before**: Only `invalid_input` documented

**After (v1.0)**:

| HTTP Status | Error Code            | Trigger                          |
| ----------- | --------------------- | -------------------------------- |
| 400         | `invalid_input`       | Missing required fields          |
| 400         | `malformed_json`      | Invalid JSON                     |
| 400         | `payload_too_large`   | Exceeds size limits              |
| 400         | `invalid_metadata`    | Incorrect metadata format        |
| 500         | `internal_error`      | Unexpected server error          |
| 503         | `service_unavailable` | Sidecar temporarily unavailable  |

**Impact**: Host system can handle all error conditions gracefully.

---

### 4. ✅ Payload Size Limits

**Before**: No limits documented

**After (v1.0)**:

| Limit                      | Value  |
| -------------------------- | ------ |
| Max `subject` length       | 500    |
| Max `latest_message` length| 10,000 |
| Max `conversation_history` | 50     |
| Max message text length    | 10,000 |
| Max `customer_name` length | 100    |
| Max `attachments` array    | 10     |
| **Total request max**      | **1MB**|

**Behavior**: Returns 400 `payload_too_large` if exceeded.

**Impact**: Prevents unbounded input, protects sidecar from abuse.

---

### 5. ✅ Clarified `processing_time_ms`

**Before**: Hardcoded to 50 (placeholder)

**After (v1.0)**:
- **Measured** end-to-end processing time (classification + draft generation)
- Excludes network latency
- Typical range: 30-100ms

**Impact**: Real performance metric for monitoring.

---

## Additional Improvements (Non-Critical)

### 6. ✅ Versioning Strategy

- Version format: `MAJOR.MINOR` (e.g., 1.0, 1.1, 2.0)
- v1.x = non-breaking changes only
- v2.0 = breaking changes allowed
- Deprecation: 90-day notice, 12-month support

### 7. ✅ Testing Requirements

Documented required test cases for:
- Request validation (5 tests)
- Intent classification (4 tests)
- Auto-send eligibility (4 tests)
- Draft generation (3 tests)
- Error handling (2 tests)

### 8. ✅ Security Considerations

- Input sanitization (host system responsibility)
- Rate limiting recommendations
- Authentication (v2.0 consideration)

---

## What's NOT Changed (Immutable)

- ✅ Intent taxonomy (9 intents)
- ✅ Intent classification logic (rule-based, deterministic)
- ✅ Draft templates (frozen)
- ✅ Safety mode rules (safe vs. unsafe)
- ✅ Confidence scoring (keyword-based)
- ✅ Draft type logic (full, clarification_only, escalation)
- ✅ Auto-send intent restriction (shipping_status ONLY)

---

## Implementation Impact

### Files to Update

1. **`app.py`**:
   - Add `auto_send_eligible` calculation
   - Add `conversation_history` validation
   - Add missing error codes
   - Add payload size checks
   - Replace hardcoded `processing_time_ms` with measured time

2. **Tests**:
   - Add v1.0 contract validation tests
   - Test all error codes
   - Test auto-send eligibility logic
   - Test payload limits

3. **Documentation**:
   - Update README with v1.0 contract link
   - Add integration guide for host system

---

## Next Steps

**Phase 3.2**: Update `app.py` to match v1.0 contract

**Required Changes**:
1. Implement `auto_send_eligible` calculation in `agent_guidance`
2. Add `conversation_history` schema validation
3. Add error codes: `malformed_json`, `payload_too_large`, `invalid_metadata`, `service_unavailable`
4. Add payload size limits enforcement
5. Measure and return actual `processing_time_ms`

**Testing**:
- Add contract validation test suite
- Verify all 18 required test cases pass

---

## Contract Lock Confirmation

🔒 **v1.0 API Contract is LOCKED**

- No breaking changes allowed
- Only additive changes in v1.x
- Breaking changes require v2.0

**Authority**: Christopher Rivero  
**Lock Date**: 2025-01-13  

---

**END OF CHANGELOG**
