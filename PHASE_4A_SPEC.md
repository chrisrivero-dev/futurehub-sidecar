# Phase 4A: Knowledge Retrieval (RAG) — Specification

**Version**: 1.0  
**Status**: 🔒 LOCKED (Awaiting Approval)  
**Date**: 2025-01-15  

---

## Overview

**Goal**: Add semantic search over knowledge base documentation to ground draft responses with authoritative sources.

**Scope**: Sidecar service only (no ticketing UI, no host system changes)

**Approach**: Additive only (no breaking changes to v1.0 API contract)

---

## Design Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Knowledge Base Access | Host system API (Option A) | Clean separation of concerns |
| Update Model | Periodic sync (Option B) | Simpler MVP, acceptable latency |
| Vector Store | ChromaDB (local) | No external dependencies |
| Embedding Model | sentence-transformers/all-MiniLM-L6-v2 | Fast, local, good quality |
| Auto-Send Impact | None | Coverage does NOT affect auto-send eligibility |
| Failure Mode | Silent degradation | Falls back to current v1.0 behavior |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 FutureHub AI Sidecar (v1.0)                  │
│                                                              │
│  ┌──────────────┐                           ┌──────────┐    │
│  │   Intent     │ ───────────────────────►  │  Draft   │    │
│  │ Classifier   │                           │Generator │    │
│  └──────────────┘                           └──────────┘    │
│         │                                          ▲         │
│         │                                          │         │
│         ▼                                          │         │
│  ┌──────────────────────────────────────────────┐│         │
│  │       Knowledge Retriever (NEW)              ││         │
│  │  ┌────────────────┐  ┌──────────────────┐   ││         │
│  │  │  Query Former  │→ │ Semantic Search  │   ││         │
│  │  └────────────────┘  └──────────────────┘   ││         │
│  │            ▼                                  ││         │
│  │  ┌─────────────────────────────────────┐    ││         │
│  │  │    ChromaDB Vector Store (Local)     │    ││         │
│  │  │  - Embedded documentation chunks     │    ││         │
│  │  │  - Metadata: intent, device, date    │    ││         │
│  │  └─────────────────────────────────────┘    ││         │
│  └──────────────────────────────────────────────┘│         │
│                         │                         │         │
│                         └─────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (periodic sync)
              ┌────────────────────────┐
              │   Host System          │
              │  Knowledge Base API    │
              │  /api/kb/articles      │
              └────────────────────────┘
```

**Flow**:
1. Intent classification (unchanged)
2. **NEW**: Query knowledge retriever with intent + message
3. **NEW**: Semantic search returns top N sources
4. **NEW**: Sources passed to draft generator (optional parameter)
5. Draft generation (templates unchanged, can optionally reference sources)
6. Response includes populated `knowledge_retrieval` block

---

## Phase 4A Implementation Phases

### **Phase 4A.1: Knowledge Retrieval Foundation (REQUIRED FOR MVP)**

**Goal**: Build RAG infrastructure

**New Modules**:
1. `knowledge_retriever.py` — Main retrieval logic
2. `embeddings.py` — Embedding generation
3. `vector_store.py` — ChromaDB interface

**Deliverables**:
- Vector store setup (ChromaDB)
- Document embedding pipeline
- Semantic search function
- Coverage scoring logic

**Integration**: None (standalone modules, not yet called by app)

**Tests**: `test_knowledge_retrieval.py`

---

### **Phase 4A.2: Response Schema Population (REQUIRED FOR MVP)**

**Goal**: Populate `knowledge_retrieval` block in API response

**Modified Files**:
1. `app_v1.py` — Add knowledge retriever call (additive)

**Changes**:
```python
# After intent classification
classification = detect_intent(...)

# NEW: Retrieve knowledge (with error handling)
try:
    knowledge = retrieve_knowledge(
        intent=classification["primary_intent"],
        message=data["latest_message"],
        metadata=classification_metadata
    )
except Exception as e:
    # Silent degradation
    knowledge = {
        "sources_consulted": [],
        "coverage": "none",
        "gaps": ["Knowledge retrieval unavailable"]
    }

# Generate draft (knowledge parameter is optional)
draft_result = generate_draft(
    classification=classification,
    customer_name=customer_name,
    metadata=classification_metadata,
    knowledge=knowledge  # NEW optional parameter
)
```

**Response Changes**: `knowledge_retrieval` block now populated (was placeholder)

**Tests**: Update `test_api_v1_contract.py` to verify knowledge_retrieval populated

---

### **Phase 4A.3: Draft Enhancement (OPTIONAL / FUTURE)**

**Goal**: Use retrieved knowledge in draft templates

**Modified Files**:
1. `draft_generator.py` — Add source references to templates (optional)

**Changes**:
```python
# Templates can optionally reference sources
if knowledge and knowledge["sources_consulted"]:
    draft += f"\n\nSee also: {knowledge['sources_consulted'][0]['title']}"
```

**Note**: This is OPTIONAL. Templates work without knowledge (v1.0 behavior preserved).

---

## Data Contracts

### 1. Knowledge Base API (Host System → Sidecar)

**Endpoint**: `GET /api/kb/articles`

**Request**:
```json
{
  "intent": "not_hashing",
  "device": "Apollo II",
  "limit": 100
}
```

**Response**:
```json
{
  "articles": [
    {
      "id": "kb-001",
      "title": "Apollo Not Hashing Troubleshooting",
      "url": "https://docs.futurebit.com/apollo-not-hashing",
      "content": "Full article text...",
      "metadata": {
        "intent": ["not_hashing", "performance_issue"],
        "device": ["Apollo", "Apollo II", "Apollo III"],
        "last_updated": "2024-12-15T10:00:00Z"
      }
    }
  ]
}
```

**Sync Frequency**: Daily (configurable)

---

### 2. Knowledge Retriever (Internal API)

**Function**: `retrieve_knowledge(intent, message, metadata)`

**Input**:
```python
{
    "intent": "not_hashing",
    "message": "My Apollo shows 0 H/s for 3 days",
    "metadata": {
        "product": "Apollo II",
        "attachments": []
    }
}
```

**Output**:
```python
{
    "sources_consulted": [
        {
            "title": "Apollo Not Hashing Troubleshooting",
            "url": "https://docs.futurebit.com/apollo-not-hashing",
            "relevance_score": 0.89,
            "excerpt": "If your Apollo shows 0 H/s, first check...",
            "last_updated": "2024-12-15T10:00:00Z"
        }
    ],
    "coverage": "high",
    "gaps": [],
    "retrieval_time_ms": 25
}
```

**Error Handling**:
```python
# On failure, return empty sources (v1.0 fallback)
{
    "sources_consulted": [],
    "coverage": "none",
    "gaps": ["Knowledge retrieval unavailable"],
    "retrieval_time_ms": 0
}
```

---

### 3. Updated Response Schema (v1.0 Compatible)

**Current (v1.0)**:
```json
"knowledge_retrieval": {
  "sources_consulted": [],
  "coverage": "none",
  "gaps": ["Knowledge retrieval not yet implemented"]
}
```

**Phase 4A (Populated)**:
```json
"knowledge_retrieval": {
  "sources_consulted": [
    {
      "title": "string",
      "url": "string",
      "relevance_score": 0.89,
      "excerpt": "string (150 chars max)",
      "last_updated": "2024-12-15T10:00:00Z"
    }
  ],
  "coverage": "high|medium|low|none",
  "gaps": [],
  "retrieval_time_ms": 25
}
```

**Changes**: All fields additive (sources populated, new fields added)

**Backwards Compatible**: Yes (existing fields preserved)

---

## MVP Scope (Required)

### ✅ REQUIRED for Phase 4A MVP

| Component | Description | Files |
|-----------|-------------|-------|
| Vector Store | ChromaDB setup + embeddings | `vector_store.py` |
| Embedding Pipeline | Document chunking + embedding | `embeddings.py` |
| Knowledge Retriever | Semantic search logic | `knowledge_retriever.py` |
| API Integration | Call retriever from app | `app_v1.py` (modified) |
| Error Handling | Silent degradation | `app_v1.py` (modified) |
| Response Population | Populate `knowledge_retrieval` | `app_v1.py` (modified) |
| Coverage Scoring | high/medium/low/none | `knowledge_retriever.py` |
| Tests | Retrieval + integration tests | `test_knowledge_retrieval.py` |

### ⏭️ OPTIONAL / Future Phases

| Component | Description | Phase |
|-----------|-------------|-------|
| Draft Enhancement | Templates reference sources | 4A.3 |
| Gap Detection | Identify missing documentation | 4A.3 |
| Real-Time Sync | Query host API on each request | 4B |
| Source Grounding Metric | Populate quality metric | 4B |
| Multi-Language Support | Non-English docs | Future |

---

## Retrieval Pipeline (MVP)

### Step 1: Query Formation

**Input**: Intent, message, metadata  
**Output**: Search query string

```python
def form_query(intent, message, metadata):
    """
    Form semantic search query from intent and message.
    
    Examples:
    - intent="not_hashing", message="0 H/s" → "Apollo not hashing 0 H/s"
    - intent="sync_delay", message="stuck at block 800000" → "Apollo sync stuck"
    """
    device = extract_device(metadata)  # "Apollo II"
    keywords = extract_keywords(message)  # ["0 H/s", "not hashing"]
    
    query = f"{device} {intent} {' '.join(keywords)}"
    return query
```

---

### Step 2: Semantic Search

**Input**: Query string  
**Output**: Top N results with scores

```python
def search(query, top_k=3, threshold=0.7):
    """
    Search vector store for relevant documents.
    
    Args:
        query: Search query string
        top_k: Number of results to return
        threshold: Minimum relevance score (0.0-1.0)
    
    Returns:
        List of (document, score) tuples
    """
    # Embed query
    query_embedding = embed(query)
    
    # Search vector store
    results = vector_store.search(
        embedding=query_embedding,
        top_k=top_k,
        threshold=threshold
    )
    
    return results
```

---

### Step 3: Metadata Filtering

**Input**: Search results  
**Output**: Filtered results

```python
def filter_results(results, intent, device):
    """
    Filter results by intent and device metadata.
    
    Example:
    - Only return docs tagged with intent="not_hashing"
    - Only return docs for device="Apollo II" (or generic "Apollo")
    """
    filtered = []
    for doc, score in results:
        if intent in doc.metadata["intent"]:
            if device in doc.metadata["device"]:
                filtered.append((doc, score))
    return filtered
```

---

### Step 4: Coverage Scoring

**Input**: Filtered results  
**Output**: Coverage label (high/medium/low/none)

```python
def score_coverage(results):
    """
    Score how well knowledge base covers the query.
    
    Rules:
    - high: 3+ results with score ≥ 0.75
    - medium: 1-2 results with score ≥ 0.6
    - low: 1+ results with score ≥ 0.4
    - none: 0 results or all scores < 0.4
    """
    if len([r for r in results if r[1] >= 0.75]) >= 3:
        return "high"
    elif len([r for r in results if r[1] >= 0.6]) >= 1:
        return "medium"
    elif len([r for r in results if r[1] >= 0.4]) >= 1:
        return "low"
    else:
        return "none"
```

---

### Step 5: Format Response

**Input**: Filtered results, coverage  
**Output**: Knowledge retrieval response

```python
def format_response(results, coverage, retrieval_time_ms):
    """
    Format knowledge retrieval response.
    """
    sources = []
    for doc, score in results[:3]:  # Top 3
        sources.append({
            "title": doc.metadata["title"],
            "url": doc.metadata["url"],
            "relevance_score": round(score, 2),
            "excerpt": doc.content[:150],
            "last_updated": doc.metadata["last_updated"]
        })
    
    return {
        "sources_consulted": sources,
        "coverage": coverage,
        "gaps": [],
        "retrieval_time_ms": retrieval_time_ms
    }
```

---

## File Structure (Phase 4A)

```
futurehub-sidecar/
├── app_v1.py                    # Modified (add retriever call)
├── intent_classifier.py         # Unchanged
├── draft_generator.py           # Unchanged (Phase 4A.1-2)
│                                # Modified (Phase 4A.3 - optional)
├── knowledge/                   # NEW directory
│   ├── __init__.py
│   ├── knowledge_retriever.py   # Main retrieval logic
│   ├── embeddings.py            # Embedding generation
│   ├── vector_store.py          # ChromaDB interface
│   └── sync.py                  # Periodic sync from host API
├── data/                        # NEW directory
│   ├── vector_store/            # ChromaDB data
│   └── articles.json            # Cached articles
├── tests/
│   ├── test_intent.py           # Unchanged
│   ├── test_draft.py            # Unchanged
│   ├── test_api_v1_contract.py  # Modified (verify knowledge populated)
│   └── test_knowledge_retrieval.py  # NEW
└── config/
    └── knowledge_config.yaml    # NEW (retrieval settings)
```

---

## Configuration

**File**: `config/knowledge_config.yaml`

```yaml
vector_store:
  provider: "chromadb"
  path: "./data/vector_store"
  collection_name: "kb_articles"

embeddings:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  dimension: 384

retrieval:
  top_k: 3
  threshold: 0.7
  timeout_ms: 100

sync:
  enabled: true
  interval: "daily"
  host_api_url: "http://localhost:3000/api/kb/articles"
```

---

## Error Handling & Degradation

### Failure Scenarios

| Failure | Cause | Behavior | User Impact |
|---------|-------|----------|-------------|
| Vector store unavailable | ChromaDB not initialized | Return empty sources | None (v1.0 fallback) |
| Retrieval timeout | Slow search (>100ms) | Return empty sources | None (v1.0 fallback) |
| Embedding failure | Model not loaded | Return empty sources | None (v1.0 fallback) |
| Host API unreachable | Sync fails | Use stale cache | Potentially outdated sources |

### Graceful Degradation Strategy

```python
def retrieve_knowledge(intent, message, metadata):
    """
    Retrieve knowledge with error handling.
    """
    try:
        # Attempt retrieval
        return _retrieve_knowledge_internal(intent, message, metadata)
    except VectorStoreError:
        logger.warning("Vector store unavailable, returning empty sources")
        return empty_sources()
    except TimeoutError:
        logger.warning("Retrieval timeout, returning empty sources")
        return empty_sources()
    except Exception as e:
        logger.error(f"Unexpected error in knowledge retrieval: {e}")
        return empty_sources()

def empty_sources():
    """Fallback to v1.0 behavior"""
    return {
        "sources_consulted": [],
        "coverage": "none",
        "gaps": ["Knowledge retrieval unavailable"],
        "retrieval_time_ms": 0
    }
```

**Critical**: No exceptions propagate to API layer. All failures return empty sources.

---

## Testing Strategy

### Unit Tests (`test_knowledge_retrieval.py`)

**Test Categories**:
1. Query formation (10 tests)
2. Semantic search (8 tests)
3. Metadata filtering (6 tests)
4. Coverage scoring (4 tests)
5. Response formatting (5 tests)
6. Error handling (7 tests)

**Example**:
```python
def test_high_coverage_three_sources():
    """3+ sources with score ≥ 0.75 → coverage = high"""
    results = [
        (doc1, 0.89),
        (doc2, 0.82),
        (doc3, 0.76)
    ]
    assert score_coverage(results) == "high"
```

---

### Integration Tests (Update `test_api_v1_contract.py`)

**New Tests**:
1. `test_knowledge_retrieval_populated()` — Verify sources present
2. `test_knowledge_retrieval_coverage_high()` — High coverage case
3. `test_knowledge_retrieval_fallback()` — Error handling
4. `test_knowledge_retrieval_does_not_affect_auto_send()` — Auto-send unchanged

**Example**:
```python
def test_knowledge_retrieval_populated(client):
    """knowledge_retrieval block is populated (not empty)"""
    payload = {
        "subject": "Apollo not working",
        "latest_message": "My Apollo shows 0 H/s",
        "conversation_history": []
    }
    
    response = client.post('/api/v1/draft', json=payload)
    data = response.get_json()
    
    kr = data["knowledge_retrieval"]
    
    # Should have sources (or gracefully degrade)
    assert "sources_consulted" in kr
    assert "coverage" in kr
    assert "retrieval_time_ms" in kr
    
    # If sources found, validate structure
    if kr["sources_consulted"]:
        source = kr["sources_consulted"][0]
        assert "title" in source
        assert "url" in source
        assert "relevance_score" in source
```

---

## Performance Requirements

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Retrieval latency (p50) | < 30ms | < 50ms |
| Retrieval latency (p95) | < 50ms | < 100ms |
| Total API latency increase | < 50ms | < 100ms |
| Vector store size | < 100MB | < 500MB |
| Embedding time per doc | < 10ms | < 50ms |

**Timeout**: 100ms (then return empty sources)

---

## Data Requirements

### Knowledge Base Content (Minimum for MVP)

**Core Documentation**:
1. Apollo Not Hashing Troubleshooting
2. Apollo Sync Troubleshooting
3. Firmware Update Instructions
4. Performance Diagnostics Guide
5. Setup & Configuration Guide
6. Shipping & Delivery FAQ
7. Warranty & RMA Process

**Total**: ~7 articles (~20-30 chunks)

**Size**: ~50KB text, ~2MB embedded

---

### Document Format (Host System)

**Example Article**:
```json
{
  "id": "kb-001",
  "title": "Apollo Not Hashing Troubleshooting",
  "url": "https://docs.futurebit.com/apollo-not-hashing",
  "content": "If your Apollo shows 0 H/s...",
  "metadata": {
    "intent": ["not_hashing"],
    "device": ["Apollo", "Apollo II", "Apollo III"],
    "last_updated": "2024-12-15T10:00:00Z",
    "author": "FutureBit Support",
    "tags": ["troubleshooting", "mining", "hashrate"]
  }
}
```

---

## Sync Process (Periodic)

### Daily Sync Flow

```
1. Fetch articles from host API
   GET /api/kb/articles?updated_since=2024-01-14

2. Identify changes
   - New articles → embed + index
   - Updated articles → re-embed + re-index
   - Deleted articles → remove from vector store

3. Update vector store
   - Chunk documents (500 words)
   - Generate embeddings
   - Insert into ChromaDB

4. Log results
   - Articles added: 3
   - Articles updated: 1
   - Articles deleted: 0
   - Sync duration: 45s
```

**Trigger**: Cron job or scheduled task (configurable)

---

## Quality Metrics (Post-MVP)

### Source Grounding Metric

**Current (v1.0)**:
```json
"quality_metrics": {
  "source_grounding": 0.0  // Placeholder
}
```

**Phase 4A (Future)**:
```json
"quality_metrics": {
  "source_grounding": 0.85  // Percentage of claims with sources
}
```

**Calculation**:
```python
# If draft references 3 facts and 2 have sources
source_grounding = 2 / 3 = 0.67
```

**Scope**: Optional / Phase 4A.3 or later

---

## Auto-Send Behavior (Unchanged)

### Critical Guarantee

**Auto-send eligibility is NOT affected by knowledge retrieval coverage.**

**Examples**:
```python
# Scenario 1: Shipping status + high coverage
coverage = "high"
auto_send_eligible = True  # (if other criteria met)

# Scenario 2: Shipping status + low coverage
coverage = "low"
auto_send_eligible = True  # (if other criteria met)

# Scenario 3: Shipping status + no coverage (retrieval failed)
coverage = "none"
auto_send_eligible = True  # (if other criteria met)
```

**Rationale**: Knowledge coverage affects draft quality, not sendability. Auto-send depends solely on intent + confidence + safety.

---

## Migration Path

### Phase 4A.1 → Production

**Step 1**: Deploy knowledge modules (no app changes yet)
```bash
# Add new modules
knowledge/knowledge_retriever.py
knowledge/embeddings.py
knowledge/vector_store.py
```

**Step 2**: Initialize vector store (one-time)
```bash
python -m knowledge.sync --initial
```

**Step 3**: Update app_v1.py (additive)
```bash
# Add knowledge retriever call
# Falls back to empty sources on error
```

**Step 4**: Verify tests pass
```bash
pytest test_api_v1_contract.py -v
pytest test_knowledge_retrieval.py -v
```

**Step 5**: Deploy to production
```bash
# No database migrations required
# No API contract changes
# Backwards compatible
```

---

## Dependencies (New)

```
chromadb==0.4.22
sentence-transformers==2.2.2
torch==2.1.0  # Required by sentence-transformers
numpy==1.24.3
```

**Size**: ~1.5GB (mostly PyTorch)

**Alternative (Lightweight)**:
```
chromadb==0.4.22
onnxruntime==1.16.0  # Instead of PyTorch
transformers==4.35.0
```

**Size**: ~300MB

---

## Success Criteria (Phase 4A MVP)

### Technical Success

- [ ] Vector store initialized with 7+ articles
- [ ] Retrieval latency < 50ms (p95)
- [ ] Coverage scoring works correctly
- [ ] Error handling degrades silently (no API failures)
- [ ] All v1.0 tests still pass
- [ ] New knowledge retrieval tests pass

### Quality Success

- [ ] High coverage (≥0.75) for common intents (not_hashing, sync_delay)
- [ ] Relevant sources returned (manual review)
- [ ] No hallucinations in excerpts
- [ ] URLs are valid and accessible

### Integration Success

- [ ] `knowledge_retrieval` block populated (not placeholder)
- [ ] Auto-send behavior unchanged
- [ ] Draft quality improved (qualitative assessment)
- [ ] No performance regression (< 100ms increase)

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Retrieval latency too high | Slow API responses | Medium | Timeout (100ms), local cache |
| Irrelevant sources | Poor draft quality | Medium | Metadata filtering, threshold tuning |
| Vector store corruption | Service failure | Low | Backup/restore, rebuild from API |
| Embedding model too large | High memory usage | Low | Use ONNX runtime (smaller) |
| Knowledge base outdated | Stale information | Medium | Daily sync, last_updated filtering |

---

## Open Questions (For Review)

### Q1: Excerpt Length
- **Current**: 150 characters
- **Alternative**: 300 characters (more context)
- **Question**: What's the right balance?

### Q2: Number of Sources
- **Current**: Top 3
- **Alternative**: Top 5 (more coverage)
- **Question**: How many sources should agents see?

### Q3: Coverage Thresholds
- **Current**: high ≥ 0.75, medium ≥ 0.6, low ≥ 0.4
- **Alternative**: Stricter (high ≥ 0.85)
- **Question**: Are thresholds too lenient?

### Q4: Sync Scheduling
- **Current**: Daily
- **Alternative**: On-demand (button in admin UI)
- **Question**: Is daily sync sufficient?

---

## Phase 4A Deliverables Checklist

### Code (New)
- [ ] `knowledge/knowledge_retriever.py`
- [ ] `knowledge/embeddings.py`
- [ ] `knowledge/vector_store.py`
- [ ] `knowledge/sync.py`

### Code (Modified)
- [ ] `app_v1.py` (add retriever call)

### Configuration
- [ ] `config/knowledge_config.yaml`

### Tests (New)
- [ ] `test_knowledge_retrieval.py` (40+ tests)

### Tests (Modified)
- [ ] `test_api_v1_contract.py` (add 4 knowledge tests)

### Documentation
- [ ] `PHASE_4A_SPEC.md` (this document)
- [ ] `KNOWLEDGE_BASE_SETUP.md` (setup guide)
- [ ] `API_CONTRACT_V1_1.md` (updated contract)

### Data
- [ ] Initial knowledge base (7+ articles)
- [ ] Vector store initialized

---

## Next Steps (After Approval)

1. ✅ Review and approve Phase 4A spec
2. ⏭️ Implement Phase 4A.1 (knowledge modules)
3. ⏭️ Implement Phase 4A.2 (API integration)
4. ⏭️ Optional: Implement Phase 4A.3 (draft enhancement)
5. ⏭️ Testing and validation

---

## Timeline Estimate

| Phase | Effort | Duration |
|-------|--------|----------|
| 4A.1: Knowledge Modules | Medium | 2-3 days |
| 4A.2: API Integration | Low | 1 day |
| 4A.3: Draft Enhancement (Optional) | Low | 1 day |
| Testing & Refinement | Medium | 1-2 days |
| **Total** | | **4-7 days** |

---

**END OF PHASE 4A SPECIFICATION**

**Status**: 🔒 Awaiting Approval

**Next Action**: Review spec, answer open questions, approve to proceed with implementation
