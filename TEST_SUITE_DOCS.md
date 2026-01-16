# Phase 3.3: Contract Validation Test Suite

**Purpose**: Validate that `app_v1.py` conforms to the locked v1.0 API contract  
**File**: `test_api_v1_contract.py`  
**Framework**: pytest  

---

## Test Categories (42 Tests Total)

### Category 1: Valid Payloads (6 tests)
Tests that valid requests are accepted and processed correctly.

| Test | Description | Validates |
|------|-------------|-----------|
| `test_valid_shipping_status_auto_send_eligible` | Shipping status with high confidence | `auto_send_eligible = true` |
| `test_valid_diagnostic_not_auto_send` | Diagnostic issue (unsafe intent) | `auto_send_eligible = false`, canned response |
| `test_valid_conversation_history` | Request with 2-message history | Conversation history processing |
| `test_valid_empty_conversation_history` | Empty conversation_history array | Empty array accepted |
| `test_valid_minimal_payload` | Only required fields | Optional fields not required |

**Key Assertion**:
```python
assert data["agent_guidance"]["auto_send_eligible"] == True  # Only for shipping_status
```

---

### Category 2: Malformed JSON (3 tests)
Tests that invalid JSON is rejected with correct error code.

| Test | Description | Expected Error |
|------|-------------|----------------|
| `test_malformed_json` | Invalid JSON syntax | 400 `malformed_json` |
| `test_empty_body` | Empty request body | 400 `malformed_json` |
| `test_null_body` | Null request body | 400 `malformed_json` |

**Contract Requirement**: Returns `malformed_json` error code, not generic 500.

---

### Category 3: Missing Required Fields (6 tests)
Tests that missing required fields are rejected.

| Test | Description | Expected Error |
|------|-------------|----------------|
| `test_missing_subject` | No `subject` field | 400 `invalid_input` |
| `test_missing_latest_message` | No `latest_message` field | 400 `invalid_input` |
| `test_missing_conversation_history` | No `conversation_history` field | 400 `invalid_input` |
| `test_null_required_field` | Required field is `null` | 400 `invalid_input` |
| `test_conversation_history_not_array` | `conversation_history` is string | 400 `invalid_input` |

**Key Assertion**:
```python
assert "subject" in data["error"]["details"]["missing_fields"]
```

---

### Category 4: Payload Size Violations (7 tests)
Tests that size limits are enforced.

| Test | Description | Limit | Expected Error |
|------|-------------|-------|----------------|
| `test_subject_too_long` | Subject > 500 chars | 500 | 400 `payload_too_large` |
| `test_latest_message_too_long` | Message > 10,000 chars | 10,000 | 400 `payload_too_large` |
| `test_conversation_history_too_many_messages` | > 50 messages | 50 | 400 `payload_too_large` |
| `test_conversation_message_text_too_long` | Message text > 10,000 chars | 10,000 | 400 `payload_too_large` |
| `test_customer_name_too_long` | Name > 100 chars | 100 | 400 `payload_too_large` |
| `test_attachments_too_many` | > 10 attachments | 10 | 400 `payload_too_large` |

**Contract Limits**:
- subject: 500 characters
- latest_message: 10,000 characters
- conversation_history: 50 messages
- customer_name: 100 characters
- attachments: 10 items
- Total request: 1MB

---

### Category 5: Conversation History Format Validation (6 tests)
Tests that conversation_history format is validated.

| Test | Description | Expected Error |
|------|-------------|----------------|
| `test_conversation_history_missing_role` | Message missing `role` | 400 `invalid_input` |
| `test_conversation_history_invalid_role` | Role is not `customer` or `agent` | 400 `invalid_input` |
| `test_conversation_history_missing_text` | Message missing `text` | 400 `invalid_input` |
| `test_conversation_history_text_not_string` | Text is number, not string | 400 `invalid_input` |
| `test_conversation_history_message_not_object` | Message is string, not object | 400 `invalid_input` |

**Valid Format**:
```json
"conversation_history": [
  {"role": "customer|agent", "text": "string", "timestamp": "optional"}
]
```

---

### Category 6: auto_send_eligible Edge Cases (6 tests)
Tests the 6 criteria for auto-send eligibility.

| Test | Description | Why auto_send_eligible = false |
|------|-------------|--------------------------------|
| `test_auto_send_eligible_wrong_intent` | `setup_help` (not shipping_status) | Wrong intent |
| `test_auto_send_eligible_low_confidence` | Vague message | Confidence < 0.85 |
| `test_auto_send_eligible_with_attachments` | Shipping status + attachments | Attachments present |
| `test_auto_send_eligible_unsafe_intent` | `not_hashing` (unsafe) | Unsafe intent |
| `test_auto_send_eligible_clarification_draft_type` | Draft type = clarification_only | Wrong draft type |

**Auto-Send Criteria (ALL must be true)**:
1. ✅ Intent is `shipping_status` (ONLY)
2. ✅ Confidence ≥ 0.85
3. ✅ Draft type is `full`
4. ✅ No attachments
5. ✅ Safety mode is `safe`
6. ✅ No ambiguity detected

---

### Category 7: Response Structure Validation (3 tests)
Tests that response conforms to v1.0 schema.

| Test | Description | Validates |
|------|-------------|-----------|
| `test_response_has_all_required_fields` | All fields present | Complete schema |
| `test_processing_time_is_measured` | processing_time_ms is realistic | Measured (not hardcoded) |
| `test_timestamp_is_valid_iso8601` | Timestamp is parseable | ISO 8601 format |

**Critical v1.0 Field**:
```python
assert "auto_send_eligible" in data["agent_guidance"]  # NEW in v1.0
```

---

### Category 8: Health Endpoint (1 test)
Tests the health check endpoint.

| Test | Description | Expected |
|------|-------------|----------|
| `test_health_endpoint` | GET /health | 200 with status, version, timestamp |

---

### Category 9: Boundary Conditions (3 tests)
Tests values at exact limits.

| Test | Description | Validates |
|------|-------------|-----------|
| `test_subject_exactly_500_chars` | Subject = 500 chars | Boundary is inclusive |
| `test_conversation_history_exactly_50_messages` | Exactly 50 messages | Boundary is inclusive |
| `test_confidence_exactly_85_percent` | Confidence = 0.85 | Threshold is >= not > |

---

## Running the Tests

### Install Dependencies
```bash
pip install pytest flask
```

### Run All Tests
```bash
pytest test_api_v1_contract.py -v
```

### Run Specific Category
```bash
# Valid payloads only
pytest test_api_v1_contract.py -k "valid" -v

# Error handling only
pytest test_api_v1_contract.py -k "malformed or missing or payload_too_large" -v

# auto_send_eligible only
pytest test_api_v1_contract.py -k "auto_send_eligible" -v
```

### Run with Coverage
```bash
pytest test_api_v1_contract.py --cov=app_v1 --cov-report=html
```

---

## Expected Results

### All Tests Should Pass ✅
```
test_api_v1_contract.py::test_valid_shipping_status_auto_send_eligible PASSED
test_api_v1_contract.py::test_valid_diagnostic_not_auto_send PASSED
test_api_v1_contract.py::test_valid_conversation_history PASSED
...
========================================== 42 passed in 2.34s ===========================================
```

### Test Failures Indicate Contract Violations
If any test fails, `app_v1.py` does not conform to the v1.0 contract.

---

## Critical Tests (Must Pass)

### 1. Auto-Send Eligibility (Top Priority)
```python
test_valid_shipping_status_auto_send_eligible()  # Must return auto_send_eligible = true
test_valid_diagnostic_not_auto_send()            # Must return auto_send_eligible = false
test_auto_send_eligible_*()                      # All edge cases
```

**Why Critical**: This is the core v1.0 feature. If these fail, auto-send logic is broken.

### 2. Conversation History Validation
```python
test_valid_conversation_history()                # Valid format accepted
test_conversation_history_*()                    # Invalid formats rejected
```

**Why Critical**: This is a new v1.0 requirement. If these fail, validation is incomplete.

### 3. Error Codes
```python
test_malformed_json()                            # Returns malformed_json code
test_missing_*()                                 # Returns invalid_input code
test_*_too_large()                               # Returns payload_too_large code
```

**Why Critical**: New error codes added in v1.0. If these fail, error handling is non-compliant.

### 4. Payload Size Limits
```python
test_subject_too_long()                          # Enforces 500 char limit
test_conversation_history_too_many_messages()    # Enforces 50 message limit
```

**Why Critical**: New limits added in v1.0. If these fail, sidecar is vulnerable to abuse.

### 5. Processing Time
```python
test_processing_time_is_measured()               # Returns measured time (not hardcoded 50)
```

**Why Critical**: Was hardcoded in Phase 2. Must be real measurement in v1.0.

---

## Test Data Summary

### Valid Payloads Used
- Shipping status with order number
- Diagnostic issue (not_hashing) with attachments
- Setup help (safe intent)
- Conversation with 2-message history
- Minimal payload (required fields only)

### Invalid Payloads Used
- Malformed JSON
- Missing required fields
- Oversized fields (subject, message, history)
- Invalid conversation_history formats
- Wrong roles, wrong types

---

## Debugging Failed Tests

### If `auto_send_eligible` tests fail:
1. Check `calculate_auto_send_eligible()` logic
2. Verify all 6 criteria are checked
3. Confirm `shipping_status` is the ONLY eligible intent

### If validation tests fail:
1. Check field size limits constants
2. Verify error_response() function
3. Confirm conversation_history validation loop

### If error code tests fail:
1. Check error_response() calls
2. Verify correct error codes returned
3. Confirm error details structure

---

## Contract Compliance Checklist

After running tests, verify:

- [ ] All 42 tests pass
- [ ] `auto_send_eligible` logic works correctly
- [ ] Conversation history validation is complete
- [ ] All error codes return correct format
- [ ] Payload size limits are enforced
- [ ] Processing time is measured (not hardcoded)
- [ ] Response structure includes all v1.0 fields
- [ ] Health endpoint works

---

## Next Steps After Tests Pass

1. ✅ **Phase 3.3 Complete**: Contract validation tests pass
2. ⏭️ **Phase 3.4**: Integration guide for host system
3. ⏭️ **Phase 4**: Knowledge base integration (future)

---

**END OF TEST SUITE DOCUMENTATION**
