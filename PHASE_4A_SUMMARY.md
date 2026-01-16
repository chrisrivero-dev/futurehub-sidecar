# Phase 4A: Knowledge Retrieval (RAG) — Summary

**Status**: 🔒 LOCKED (Awaiting Approval)  
**Date**: 2025-01-15  

---

## Quick Overview

**Goal**: Add semantic search over knowledge base to ground AI drafts with authoritative documentation.

**Approach**: Additive only — no breaking changes to v1.0 API contract.

**Key Decisions**:
- Knowledge base via host system API
- Local vector store (ChromaDB)
- Periodic sync (daily)
- sentence-transformers embeddings
- Auto-send logic UNCHANGED
- Silent degradation on failures

---

## What Phase 4A Adds

### Current State (v1.0)
```json
"knowledge_retrieval": {
  "sources_consulted": [],
  "coverage": "none",
  "gaps": ["Knowledge retrieval not yet implemented"]
}
```

### Phase 4A State
```json
"knowledge_retrieval": {
  "sources_consulted": [
    {
      "title": "Apollo Not Hashing Troubleshooting",
      "url": "https://docs.futurebit.com/apollo-not-hashing",
      "relevance_score": 0.89,
      "excerpt": "If your Apollo shows 0 H/s...",
      "last_updated": "2024-12-15T10:00:00Z"
    }
  ],
  "coverage": "high",
  "gaps": [],
  "retrieval_time_ms": 28
}
```

**Change**: Placeholder data → Real knowledge base sources

---

## Architecture

```
app_v1.py
   │
   ├─► classify_intent()        [UNCHANGED]
   │
   ├─► retrieve_knowledge()     [NEW]
   │      │
   │      └─► vector_store.search()
   │             │
   │             └─► ChromaDB (local)
   │
   └─► generate_draft()         [UNCHANGED - MVP]
                                [OPTIONAL - Phase 4A.3: Use sources]
```

---

## Implementation Phases

### ✅ Phase 4A.1: Knowledge Foundation (REQUIRED)

**Goal**: Build RAG infrastructure

**New Files**:
- `knowledge/knowledge_retriever.py` — Main retrieval logic
- `knowledge/embeddings.py` — Embedding generation
- `knowledge/vector_store.py` — ChromaDB interface
- `knowledge/sync.py` — Periodic sync from host API

**Deliverables**:
- Vector store setup (ChromaDB)
- Document embedding pipeline
- Semantic search function
- Coverage scoring logic

**Tests**: `test_knowledge_retrieval.py` (40+ tests)

**No app changes yet** — standalone modules

---

### ✅ Phase 4A.2: API Integration (REQUIRED)

**Goal**: Populate `knowledge_retrieval` block in API response

**Modified Files**:
- `app_v1.py` — Add knowledge retriever call (20 lines)

**Changes**:
```python
# After intent classification
classification = detect_intent(...)

# NEW: Retrieve knowledge
try:
    knowledge = retrieve_knowledge(
        intent=classification["primary_intent"],
        message=data["latest_message"],
        metadata=metadata
    )
except Exception:
    knowledge = empty_sources()  # Fallback to v1.0

# Generate draft (unchanged)
draft_result = generate_draft(
    classification=classification,
    customer_name=customer_name,
    metadata=metadata,
    knowledge=knowledge  # NEW optional parameter (not used yet)
)

# knowledge added to response (was placeholder)
```

**Tests**: Update `test_api_v1_contract.py` (add 4 tests)

---

### ⏭️ Phase 4A.3: Draft Enhancement (OPTIONAL)

**Goal**: Use retrieved knowledge in draft templates

**Modified Files**:
- `draft_generator.py` — Add source references (optional)

**Changes**:
```python
# Templates MAY reference sources
if knowledge and knowledge["sources_consulted"]:
    draft += f"\n\nSee also: {knowledge['sources_consulted'][0]['title']}"
```

**Note**: This is OPTIONAL. Templates work without knowledge (v1.0 behavior).

---

## MVP Scope

### ✅ REQUIRED for Phase 4A MVP

| Component | Description | Complexity |
|-----------|-------------|------------|
| Vector Store Setup | ChromaDB + embeddings | Medium |
| Knowledge Retriever | Semantic search logic | Medium |
| API Integration | Call retriever from app | Low |
| Error Handling | Silent degradation | Low |
| Coverage Scoring | high/medium/low/none | Low |
| Testing | Retrieval + integration tests | Medium |

**Total Effort**: 3-4 days

---

### ⏭️ OPTIONAL / Future Phases

| Component | Description | Phase |
|-----------|-------------|-------|
| Draft Enhancement | Templates reference sources | 4A.3 |
| Gap Detection | Identify missing docs | 4A.3 |
| Real-Time Sync | Query host API live | 4B |
| Source Grounding | Populate quality metric | 4B |

---

## Data Contracts

### 1. Host Knowledge Base API

**Endpoint**: `GET /api/kb/articles`

**Response**:
```json
{
  "articles": [
    {
      "id": "kb-001",
      "title": "Apollo Not Hashing Troubleshooting",
      "url": "https://docs.futurebit.com/...",
      "content": "Full article text...",
      "metadata": {
        "intent": ["not_hashing"],
        "device": ["Apollo", "Apollo II"],
        "last_updated": "2024-12-15T10:00:00Z"
      }
    }
  ]
}
```

---

### 2. Knowledge Retriever (Internal)

**Function**: `retrieve_knowledge(intent, message, metadata)`

**Input**:
```python
{
    "intent": "not_hashing",
    "message": "My Apollo shows 0 H/s",
    "metadata": {"product": "Apollo II"}
}
```

**Output**:
```python
{
    "sources_consulted": [...],  # Top 3 sources
    "coverage": "high",          # high/medium/low/none
    "gaps": [],                  # Missing topics
    "retrieval_time_ms": 28      # Latency
}
```

**Error Handling**: Never raises, returns empty sources on failure

---

## Key Guarantees

### 1. Backwards Compatible
- ✅ All v1.0 tests still pass
- ✅ Existing fields preserved
- ✅ New fields additive only
- ✅ Empty sources = v1.0 behavior

### 2. Auto-Send Unchanged
- ✅ Coverage does NOT affect auto-send eligibility
- ✅ shipping_status still auto-send eligible
- ✅ Unsafe intents still require review
- ✅ All 6 auto-send criteria unchanged

### 3. Silent Degradation
- ✅ Vector store unavailable → empty sources
- ✅ Retrieval timeout (>100ms) → empty sources
- ✅ Embedding failure → empty sources
- ✅ No new 500 errors introduced

### 4. Performance
- ✅ Retrieval latency < 50ms (p95)
- ✅ Total API latency increase < 100ms
- ✅ Timeout at 100ms (then fallback)

---

## Coverage Scoring

| Coverage | Criteria | Example |
|----------|----------|---------|
| `high` | 3+ sources, score ≥ 0.75 | Intent has dedicated guide |
| `medium` | 1-2 sources, score ≥ 0.6 | Partial match |
| `low` | 1+ sources, score ≥ 0.4 | Generic only |
| `none` | 0 sources or score < 0.4 | No relevant docs |

**Note**: Coverage affects draft quality signals, NOT auto-send eligibility.

---

## Error Handling

### All Failures Return Empty Sources

```python
# On ANY error
{
    "sources_consulted": [],
    "coverage": "none",
    "gaps": ["Knowledge retrieval unavailable"],
    "retrieval_time_ms": 0
}
```

**No exceptions propagate to API layer.**

---

## File Changes Summary

### New Files (Phase 4A.1)
```
knowledge/
├── __init__.py
├── knowledge_retriever.py   # Main retrieval logic
├── embeddings.py            # Embedding generation
├── vector_store.py          # ChromaDB interface
└── sync.py                  # Periodic sync

tests/
└── test_knowledge_retrieval.py  # New tests
```

### Modified Files (Phase 4A.2)
```
app_v1.py                    # Add retriever call (~20 lines)
test_api_v1_contract.py      # Add 4 knowledge tests
```

### Optional (Phase 4A.3)
```
draft_generator.py           # Add source references (optional)
```

---

## Testing Requirements

### New Tests (`test_knowledge_retrieval.py`)
- Query formation: 10 tests
- Semantic search: 8 tests
- Metadata filtering: 6 tests
- Coverage scoring: 4 tests
- Response formatting: 5 tests
- Error handling: 7 tests

**Total**: 40+ tests

### Updated Tests (`test_api_v1_contract.py`)
- `test_knowledge_retrieval_populated()` — Verify sources
- `test_knowledge_retrieval_coverage()` — Coverage scoring
- `test_knowledge_retrieval_fallback()` — Error handling
- `test_knowledge_retrieval_auto_send_unchanged()` — Auto-send unaffected

**Total**: 4 additional tests

---

## Performance Budget

| Metric | Target | Maximum |
|--------|--------|---------|
| Retrieval latency (p50) | < 30ms | < 50ms |
| Retrieval latency (p95) | < 50ms | < 100ms |
| Total API increase | < 50ms | < 100ms |
| Vector store size | < 100MB | < 500MB |

---

## Minimum Knowledge Base Content

**Required for MVP**:
1. Apollo Not Hashing Troubleshooting
2. Apollo Sync Troubleshooting
3. Firmware Update Instructions
4. Performance Diagnostics Guide
5. Setup & Configuration Guide
6. Shipping & Delivery FAQ
7. Warranty & RMA Process

**Total**: ~7 articles (~20-30 chunks after splitting)

**Size**: ~50KB text, ~2MB embedded

---

## Dependencies (New)

### Option 1: Full PyTorch
```
chromadb==0.4.22
sentence-transformers==2.2.2
torch==2.1.0
```
**Size**: ~1.5GB

### Option 2: Lightweight (RECOMMENDED)
```
chromadb==0.4.22
onnxruntime==1.16.0
transformers==4.35.0
```
**Size**: ~300MB

---

## Success Criteria

### Technical ✅
- [ ] Vector store initialized with 7+ articles
- [ ] Retrieval latency < 50ms (p95)
- [ ] Coverage scoring correct
- [ ] Error handling degrades silently
- [ ] All v1.0 tests pass
- [ ] All new tests pass

### Quality ✅
- [ ] High coverage for common intents
- [ ] Relevant sources returned
- [ ] No hallucinations in excerpts
- [ ] Valid, accessible URLs

### Integration ✅
- [ ] `knowledge_retrieval` populated
- [ ] Auto-send unchanged
- [ ] No performance regression
- [ ] Backwards compatible

---

## Open Questions

### Q1: Excerpt Length
- Current: 150 characters
- Alternative: 300 characters
- **Question**: Right balance?

### Q2: Number of Sources
- Current: Top 3
- Alternative: Top 5
- **Question**: How many sources?

### Q3: Coverage Thresholds
- Current: high ≥ 0.75, medium ≥ 0.6
- Alternative: Stricter thresholds
- **Question**: Too lenient?

### Q4: Sync Frequency
- Current: Daily
- Alternative: On-demand
- **Question**: Sufficient?

---

## Timeline

| Phase | Effort | Duration |
|-------|--------|----------|
| 4A.1: Knowledge Modules | Medium | 2-3 days |
| 4A.2: API Integration | Low | 1 day |
| Testing & Refinement | Medium | 1-2 days |
| **Total (MVP)** | | **4-6 days** |
| 4A.3: Draft Enhancement (Optional) | Low | 1 day |

---

## Next Steps

1. ✅ **Review Phase 4A spec**
2. ✅ **Answer open questions**
3. ⏭️ **Approve to proceed with 4A.1**
4. ⏭️ **Implement knowledge modules**
5. ⏭️ **Integrate with app_v1.py**
6. ⏭️ **Test and validate**

---

## Deliverables Checklist

### Phase 4A.1 (REQUIRED)
- [ ] `knowledge/knowledge_retriever.py`
- [ ] `knowledge/embeddings.py`
- [ ] `knowledge/vector_store.py`
- [ ] `knowledge/sync.py`
- [ ] `test_knowledge_retrieval.py`

### Phase 4A.2 (REQUIRED)
- [ ] `app_v1.py` (modified)
- [ ] `test_api_v1_contract.py` (updated)
- [ ] Initial knowledge base (7 articles)
- [ ] Vector store initialized

### Phase 4A.3 (OPTIONAL)
- [ ] `draft_generator.py` (modified)

---

**END OF PHASE 4A SUMMARY**

**Status**: 🔒 Awaiting Approval

**Key Decision Points**:
1. Approve overall approach?
2. Answer open questions (Q1-Q4)?
3. Proceed with Phase 4A.1 implementation?
