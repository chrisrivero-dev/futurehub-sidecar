# Phase 4A: Knowledge Retrieval — Data Contracts

**Purpose**: Define minimal input/output contracts for knowledge retrieval integration

---

## Contract 1: Host Knowledge Base API

**Owner**: Host system  
**Consumer**: FutureHub Sidecar  

### Endpoint

```
GET /api/kb/articles
```

### Request Parameters

```json
{
  "intent": "not_hashing",           // Optional: Filter by intent
  "device": "Apollo II",             // Optional: Filter by device
  "updated_since": "2024-01-14",     // Optional: Only articles updated after date
  "limit": 100                       // Optional: Max results (default 100)
}
```

### Response (Success - 200)

```json
{
  "articles": [
    {
      "id": "kb-001",
      "title": "Apollo Not Hashing Troubleshooting",
      "url": "https://docs.futurebit.com/apollo-not-hashing",
      "content": "If your Apollo shows 0 H/s...",  // Full article text
      "metadata": {
        "intent": ["not_hashing", "performance_issue"],
        "device": ["Apollo", "Apollo II", "Apollo III"],
        "last_updated": "2024-12-15T10:00:00Z",
        "author": "FutureBit Support"
      }
    }
  ],
  "total": 25,
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Response (Error - 500)

```json
{
  "error": "Internal server error",
  "message": "Knowledge base unavailable"
}
```

### Guarantees

- ✅ Returns all articles if no filters provided
- ✅ Articles include full content (not excerpts)
- ✅ `last_updated` timestamp always present
- ✅ Response is paginated if > limit
- ❌ Real-time updates (not required for MVP)

---

## Contract 2: Knowledge Retriever (Internal)

**Owner**: FutureHub Sidecar  
**Consumer**: app_v1.py  

### Function Signature

```python
def retrieve_knowledge(intent: str, message: str, metadata: dict) -> dict:
    """
    Retrieve relevant knowledge base articles for a support query.
    
    Args:
        intent: Primary intent from classification (e.g., "not_hashing")
        message: Customer's latest message text
        metadata: Dict with optional "product" and "attachments" keys
    
    Returns:
        dict with keys: sources_consulted, coverage, gaps, retrieval_time_ms
    
    Raises:
        Never raises (returns empty sources on error)
    """
```

### Input

```python
{
    "intent": "not_hashing",
    "message": "My Apollo shows 0 H/s for 3 days. Already tried restarting.",
    "metadata": {
        "product": "Apollo II",
        "attachments": ["debug.log"]
    }
}
```

### Output (Success)

```python
{
    "sources_consulted": [
        {
            "title": "Apollo Not Hashing Troubleshooting",
            "url": "https://docs.futurebit.com/apollo-not-hashing",
            "relevance_score": 0.89,
            "excerpt": "If your Apollo shows 0 H/s, first check that your pool configuration is correct...",
            "last_updated": "2024-12-15T10:00:00Z"
        },
        {
            "title": "Apollo II Hashrate Issues",
            "url": "https://docs.futurebit.com/apollo-ii-hashrate",
            "relevance_score": 0.82,
            "excerpt": "Apollo II devices may show 0 H/s if the Bitcoin node is not fully synced...",
            "last_updated": "2024-11-20T14:30:00Z"
        }
    ],
    "coverage": "high",
    "gaps": [],
    "retrieval_time_ms": 28
}
```

### Output (No Results / Low Coverage)

```python
{
    "sources_consulted": [
        {
            "title": "General Mining Troubleshooting",
            "url": "https://docs.futurebit.com/mining-basics",
            "relevance_score": 0.45,
            "excerpt": "Mining devices may experience issues for various reasons...",
            "last_updated": "2024-10-01T09:00:00Z"
        }
    ],
    "coverage": "low",
    "gaps": ["No Apollo II specific troubleshooting guide for this issue"],
    "retrieval_time_ms": 32
}
```

### Output (Error / Fallback)

```python
{
    "sources_consulted": [],
    "coverage": "none",
    "gaps": ["Knowledge retrieval unavailable"],
    "retrieval_time_ms": 0
}
```

### Field Specifications

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sources_consulted` | array | ✅ Yes | Top 3 relevant articles (empty array if none) |
| `coverage` | string | ✅ Yes | "high" / "medium" / "low" / "none" |
| `gaps` | array | ✅ Yes | Missing documentation topics (empty if full coverage) |
| `retrieval_time_ms` | int | ✅ Yes | Time to retrieve (0 if failed) |

### Source Object Schema

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `title` | string | ✅ Yes | 200 chars | Article title |
| `url` | string | ✅ Yes | 500 chars | Article URL |
| `relevance_score` | float | ✅ Yes | 0.0-1.0 | Semantic similarity score |
| `excerpt` | string | ✅ Yes | 150 chars | Article snippet |
| `last_updated` | string | ✅ Yes | ISO 8601 | Last update timestamp |

### Guarantees

- ✅ Never raises exceptions (returns empty on error)
- ✅ Always returns within 100ms (or times out)
- ✅ Returns max 3 sources (top_k=3)
- ✅ Only returns sources with relevance_score ≥ 0.7
- ✅ Empty array if no sources meet threshold

---

## Contract 3: Updated API Response (v1.0 → v1.1)

**Owner**: FutureHub Sidecar  
**Consumer**: Host system / Agents  

### Change Summary

**v1.0 (Current)**:
```json
"knowledge_retrieval": {
  "sources_consulted": [],
  "coverage": "none",
  "gaps": ["Knowledge retrieval not yet implemented"]
}
```

**v1.1 (Phase 4A)**:
```json
"knowledge_retrieval": {
  "sources_consulted": [
    {
      "title": "string",
      "url": "string",
      "relevance_score": 0.89,
      "excerpt": "string",
      "last_updated": "2024-12-15T10:00:00Z"
    }
  ],
  "coverage": "high",
  "gaps": [],
  "retrieval_time_ms": 28
}
```

### New Fields

| Field | Type | Description | Backwards Compatible |
|-------|------|-------------|----------------------|
| `retrieval_time_ms` | int | Retrieval latency | ✅ Yes (additive) |
| `relevance_score` (in sources) | float | Semantic similarity | ✅ Yes (additive) |
| `excerpt` (in sources) | string | Article snippet | ✅ Yes (additive) |
| `last_updated` (in sources) | string | Update timestamp | ✅ Yes (additive) |

### Changed Fields

| Field | v1.0 | v1.1 | Backwards Compatible |
|-------|------|------|----------------------|
| `sources_consulted` | Always `[]` | Array of objects (may be empty) | ✅ Yes |
| `coverage` | Always `"none"` | "high" / "medium" / "low" / "none" | ✅ Yes |
| `gaps` | Placeholder message | Actual gaps or empty array | ✅ Yes |

### Compatibility Guarantee

**All v1.0 clients continue to work**:
- Existing fields remain
- New fields are additive
- Empty arrays still valid
- Semantics unchanged

---

## Contract 4: Draft Generator (Internal Update)

**Owner**: FutureHub Sidecar  
**Consumer**: app_v1.py  

### Current Signature (v1.0)

```python
def generate_draft(classification, customer_name=None, metadata=None):
    """Generate draft response based on intent classification."""
```

### Updated Signature (Phase 4A)

```python
def generate_draft(classification, customer_name=None, metadata=None, knowledge=None):
    """
    Generate draft response based on intent classification.
    
    Args:
        classification: Intent classification result
        customer_name: Optional customer name
        metadata: Optional metadata dict
        knowledge: Optional knowledge retrieval result (NEW)
    
    Returns:
        dict with draft text and metadata
    """
```

### Behavior

**If `knowledge` is None or empty sources**:
- Generate draft exactly as v1.0 (templates unchanged)
- No references to sources

**If `knowledge` has sources** (Phase 4A.3 - OPTIONAL):
- Templates MAY reference sources
- Example: "See also: Apollo Not Hashing Troubleshooting"

### Compatibility

- ✅ v1.0 behavior preserved (knowledge parameter optional)
- ✅ All existing tests pass unchanged
- ✅ No breaking changes to templates

---

## Data Flow (Phase 4A)

```
┌─────────────────────────────────────────────────────────────┐
│                        app_v1.py                             │
│                                                              │
│  1. Receive request                                          │
│  2. Classify intent ────────────────────┐                    │
│                                         ▼                    │
│  3. Retrieve knowledge ────────► retrieve_knowledge()        │
│     Input:                              │                    │
│     - intent: "not_hashing"             │                    │
│     - message: "0 H/s"                  │                    │
│     - metadata: {product}               │                    │
│                                         ▼                    │
│     Output:                       [Query Vector Store]       │
│     - sources_consulted: [...]          │                    │
│     - coverage: "high"                  │                    │
│     - gaps: []                          │                    │
│                                         │                    │
│  4. Generate draft ◄────────────────────┘                    │
│     Input:                                                   │
│     - classification                                         │
│     - knowledge (optional)                                   │
│                                                              │
│  5. Build response                                           │
│     - intent_classification: {...}                           │
│     - draft: {...}                                           │
│     - knowledge_retrieval: {...}  ← Populated                │
│     - agent_guidance: {...}                                  │
│                                                              │
│  6. Return JSON                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling Contract

### Error Types & Responses

| Error Type | Cause | Sidecar Behavior | API Response |
|------------|-------|------------------|--------------|
| Vector store unavailable | ChromaDB not initialized | Return empty sources | 200 OK (degraded) |
| Embedding model error | Model not loaded | Return empty sources | 200 OK (degraded) |
| Retrieval timeout | Search > 100ms | Return empty sources | 200 OK (degraded) |
| Host API unreachable | Sync failed | Use stale cache | 200 OK (may be outdated) |
| Invalid query | Malformed input | Return empty sources | 200 OK (degraded) |

### Critical Guarantee

**No new 500 errors**: All knowledge retrieval failures result in empty sources (v1.0 fallback), not API errors.

**Example**:
```python
try:
    knowledge = retrieve_knowledge(...)
except Exception:
    knowledge = {
        "sources_consulted": [],
        "coverage": "none",
        "gaps": ["Knowledge retrieval unavailable"]
    }
    # Continue normally
```

---

## Performance Contract

### Latency Budget

| Component | Target | Maximum |
|-----------|--------|---------|
| Query formation | < 5ms | < 10ms |
| Vector search | < 20ms | < 50ms |
| Metadata filtering | < 5ms | < 10ms |
| Response formatting | < 5ms | < 10ms |
| **Total retrieval** | **< 35ms** | **< 100ms** |

**Timeout**: 100ms (hard limit)

### Throughput

| Metric | Target | Notes |
|--------|--------|-------|
| Concurrent requests | 50 | Per sidecar instance |
| Cache hit rate | > 80% | For repeated queries |
| Vector store size | < 100MB | For MVP (7 articles) |

---

## Testing Contract

### Unit Test Coverage

| Module | Coverage Target | Critical Tests |
|--------|----------------|----------------|
| `knowledge_retriever.py` | > 90% | Query formation, search, scoring |
| `embeddings.py` | > 85% | Embedding generation, chunking |
| `vector_store.py` | > 85% | CRUD operations, search |

### Integration Test Requirements

**Required Tests** (add to `test_api_v1_contract.py`):
1. `test_knowledge_retrieval_populated()` — Verify sources returned
2. `test_knowledge_retrieval_empty_on_failure()` — Error handling
3. `test_knowledge_retrieval_latency()` — Performance
4. `test_knowledge_retrieval_does_not_break_auto_send()` — Auto-send unchanged

---

## Summary: MVP Data Contracts

### ✅ REQUIRED for Phase 4A MVP

1. **Host Knowledge Base API**
   - Endpoint: `GET /api/kb/articles`
   - Returns: Articles with metadata

2. **Knowledge Retriever Function**
   - Input: intent, message, metadata
   - Output: sources, coverage, gaps, time
   - Error handling: Silent degradation

3. **Updated API Response**
   - Populate `knowledge_retrieval` block
   - Backwards compatible
   - New fields additive

### ⏭️ OPTIONAL / Future

1. **Draft Generator Enhancement** (Phase 4A.3)
   - Accept knowledge parameter
   - Reference sources in templates

2. **Real-Time Sync** (Phase 4B)
   - Query host API on each request
   - No local cache

3. **Advanced Metrics** (Phase 4B)
   - Source grounding calculation
   - Gap analysis

---

**END OF DATA CONTRACTS**
