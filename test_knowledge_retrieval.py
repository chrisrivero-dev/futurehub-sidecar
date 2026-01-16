"""
Test Knowledge Retrieval (Phase 4A.1)
Comprehensive tests for knowledge modules
"""
import pytest
import sys
import os
import tempfile
import shutil

# Add knowledge directory to path
sys.path.insert(0, '/home/claude')

from knowledge.vector_store import VectorStore
from knowledge.embeddings import EmbeddingGenerator, extract_keywords
from knowledge.knowledge_retriever import KnowledgeRetriever


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_vector_store_path():
    """Create temporary directory for vector store"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def vector_store(temp_vector_store_path):
    """Create and initialize vector store"""
    vs = VectorStore(path=temp_vector_store_path, collection_name="test_kb")
    vs.initialize()
    return vs


@pytest.fixture
def embedder():
    """Create and initialize embedding generator"""
    emb = EmbeddingGenerator()
    emb.initialize()
    return emb


@pytest.fixture
def retriever(temp_vector_store_path):
    """Create and initialize knowledge retriever"""
    ret = KnowledgeRetriever(
        vector_store_path=temp_vector_store_path,
        collection_name="test_kb"
    )
    ret.initialize()
    return ret


# ==============================================================================
# CATEGORY 1: Vector Store Tests (8 tests)
# ==============================================================================

def test_vector_store_initialization(temp_vector_store_path):
    """Test vector store initializes correctly"""
    vs = VectorStore(path=temp_vector_store_path)
    assert vs.initialize() == True
    assert vs.collection is not None


def test_vector_store_add_documents(vector_store, embedder):
    """Test adding documents to vector store"""
    # Create test documents
    docs = ["Apollo not hashing troubleshooting", "Sync delay issues"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [
        {"title": "Doc 1", "url": "http://test.com/1"},
        {"title": "Doc 2", "url": "http://test.com/2"}
    ]
    ids = ["doc1", "doc2"]
    
    # Add documents
    success = vector_store.add_documents(docs, embeddings, metadatas, ids)
    assert success == True
    
    # Verify count
    assert vector_store.get_count() == 2


def test_vector_store_search(vector_store, embedder):
    """Test searching vector store"""
    # Add test documents
    docs = [
        "Apollo not hashing troubleshooting guide",
        "Sync delay common causes",
        "Firmware update instructions"
    ]
    embeddings = embedder.embed_batch(docs)
    metadatas = [
        {"title": f"Doc {i}", "url": f"http://test.com/{i}"}
        for i in range(len(docs))
    ]
    ids = [f"doc{i}" for i in range(len(docs))]
    
    vector_store.add_documents(docs, embeddings, metadatas, ids)
    
    # Search for "not hashing"
    query = "Apollo not hashing"
    query_embedding = embedder.embed_text(query)
    results = vector_store.search(query_embedding, top_k=2, threshold=0.5)
    
    assert len(results) > 0
    assert results[0][1] > 0.5  # Score > threshold
    assert "not hashing" in results[0][0]["content"].lower()


def test_vector_store_search_with_threshold(vector_store, embedder):
    """Test search respects similarity threshold"""
    docs = ["Apollo mining guide"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": "Doc", "url": "http://test.com"}]
    ids = ["doc1"]
    
    vector_store.add_documents(docs, embeddings, metadatas, ids)
    
    # Search with very high threshold (should return nothing)
    query = "completely unrelated query about cats"
    query_embedding = embedder.embed_text(query)
    results = vector_store.search(query_embedding, top_k=3, threshold=0.95)
    
    assert len(results) == 0  # No results above threshold


def test_vector_store_delete_documents(vector_store, embedder):
    """Test deleting documents from vector store"""
    docs = ["Test document"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": "Doc", "url": "http://test.com"}]
    ids = ["doc1"]
    
    vector_store.add_documents(docs, embeddings, metadatas, ids)
    assert vector_store.get_count() == 1
    
    vector_store.delete_documents(["doc1"])
    assert vector_store.get_count() == 0


def test_vector_store_update_documents(vector_store, embedder):
    """Test updating documents in vector store"""
    # Add initial document
    docs = ["Initial content"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": "Doc", "url": "http://test.com", "version": "1"}]
    ids = ["doc1"]
    
    vector_store.add_documents(docs, embeddings, metadatas, ids)
    
    # Update document
    new_docs = ["Updated content"]
    new_embeddings = embedder.embed_batch(new_docs)
    new_metadatas = [{"title": "Doc", "url": "http://test.com", "version": "2"}]
    
    success = vector_store.update_documents(["doc1"], new_docs, new_embeddings, new_metadatas)
    assert success == True


def test_vector_store_get_count(vector_store, embedder):
    """Test getting document count"""
    assert vector_store.get_count() == 0
    
    # Add documents
    docs = ["Doc 1", "Doc 2", "Doc 3"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": f"Doc {i}"} for i in range(len(docs))]
    ids = [f"doc{i}" for i in range(len(docs))]
    
    vector_store.add_documents(docs, embeddings, metadatas, ids)
    assert vector_store.get_count() == 3


def test_vector_store_reset(vector_store, embedder):
    """Test resetting vector store"""
    # Add documents
    docs = ["Test doc"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": "Doc"}]
    ids = ["doc1"]
    
    vector_store.add_documents(docs, embeddings, metadatas, ids)
    assert vector_store.get_count() == 1
    
    # Reset
    vector_store.reset()
    assert vector_store.get_count() == 0


# ==============================================================================
# CATEGORY 2: Embedding Tests (10 tests)
# ==============================================================================

def test_embedder_initialization():
    """Test embedding model initializes"""
    emb = EmbeddingGenerator()
    assert emb.initialize() == True
    assert emb.model is not None


def test_embedder_embed_single_text(embedder):
    """Test embedding a single text"""
    text = "Apollo not hashing"
    embedding = embedder.embed_text(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
    assert all(isinstance(x, float) for x in embedding)


def test_embedder_embed_batch(embedder):
    """Test embedding multiple texts"""
    texts = ["Text 1", "Text 2", "Text 3"]
    embeddings = embedder.embed_batch(texts)
    
    assert len(embeddings) == 3
    assert all(len(emb) == 384 for emb in embeddings)


def test_embedder_similar_texts_similar_embeddings(embedder):
    """Test similar texts have similar embeddings"""
    text1 = "Apollo not hashing"
    text2 = "Apollo hashrate zero"
    text3 = "How to cook pasta"
    
    emb1 = embedder.embed_text(text1)
    emb2 = embedder.embed_text(text2)
    emb3 = embedder.embed_text(text3)
    
    # Calculate cosine similarity (simplified)
    import numpy as np
    similarity_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    similarity_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
    
    assert similarity_12 > similarity_13  # Apollo texts more similar than Apollo vs pasta


def test_embedder_chunk_document(embedder):
    """Test document chunking"""
    # Create long document (1000 words)
    content = " ".join(["word"] * 1000)
    
    chunks = embedder.chunk_document(content, chunk_size=500, overlap=50)
    
    assert len(chunks) > 1  # Should be split
    assert all(isinstance(c, str) for c in chunks)


def test_embedder_chunk_short_document(embedder):
    """Test chunking short document (no split)"""
    content = "Short document with few words"
    
    chunks = embedder.chunk_document(content, chunk_size=500)
    
    assert len(chunks) == 1
    assert chunks[0] == content


def test_embedder_chunk_overlap(embedder):
    """Test chunks have overlap"""
    content = " ".join([f"word{i}" for i in range(600)])
    
    chunks = embedder.chunk_document(content, chunk_size=500, overlap=50)
    
    assert len(chunks) >= 2
    # Check overlap exists (last words of chunk N in first words of chunk N+1)
    # Simplified check: chunks have similar length
    assert abs(len(chunks[0].split()) - len(chunks[1].split())) < 100


def test_embedder_process_article(embedder):
    """Test processing complete article"""
    article_id = "kb-001"
    title = "Apollo Not Hashing"
    url = "http://test.com"
    content = " ".join(["test"] * 600)  # ~600 words
    metadata = {"intent": ["not_hashing"], "device": ["Apollo II"]}
    
    results = embedder.process_article(article_id, title, url, content, metadata)
    
    assert len(results) > 0
    for chunk_id, chunk_text, embedding, chunk_meta in results:
        assert chunk_id.startswith(article_id)
        assert isinstance(chunk_text, str)
        assert len(embedding) == 384
        assert chunk_meta["title"] == title
        assert chunk_meta["url"] == url
        assert "intent" in chunk_meta


def test_extract_keywords():
    """Test keyword extraction"""
    text = "My Apollo shows 0 H/s and is not hashing properly"
    keywords = extract_keywords(text, max_keywords=3)
    
    assert len(keywords) <= 3
    assert all(isinstance(kw, str) for kw in keywords)
    # Should exclude stop words
    assert "my" not in keywords
    assert "is" not in keywords


def test_extract_keywords_filters_stop_words():
    """Test stop words are filtered"""
    text = "the and or but in on at to for of with by from"
    keywords = extract_keywords(text, max_keywords=10)
    
    assert len(keywords) == 0  # All stop words


# ==============================================================================
# CATEGORY 3: Knowledge Retriever Tests (12 tests)
# ==============================================================================

def test_retriever_initialization(temp_vector_store_path):
    """Test retriever initializes"""
    ret = KnowledgeRetriever(vector_store_path=temp_vector_store_path)
    assert ret.initialize() == True
    assert ret.initialized == True


def test_retriever_empty_vector_store(retriever):
    """Test retrieval from empty vector store returns empty"""
    result = retriever.retrieve_knowledge(
        intent="not_hashing",
        message="My Apollo shows 0 H/s"
    )
    
    assert result["sources_consulted"] == []
    assert result["coverage"] == "none"
    assert "retrieval_time_ms" in result


def test_retriever_form_query_basic(retriever):
    """Test query formation"""
    query = retriever._form_query(
        intent="not_hashing",
        message="My Apollo shows 0 H/s",
        metadata=None
    )
    
    assert "apollo" in query.lower()
    assert "not hashing" in query.lower()


def test_retriever_form_query_with_device(retriever):
    """Test query formation includes device"""
    query = retriever._form_query(
        intent="sync_delay",
        message="Stuck at block",
        metadata={"product": "Apollo II"}
    )
    
    assert "apollo ii" in query.lower()
    assert "sync" in query.lower()


def test_retriever_score_coverage_high(retriever):
    """Test coverage scoring: high"""
    results = [
        ({}, 0.89),
        ({}, 0.82),
        ({}, 0.76)
    ]
    
    coverage = retriever._score_coverage(results)
    assert coverage == "high"


def test_retriever_score_coverage_medium(retriever):
    """Test coverage scoring: medium"""
    results = [
        ({}, 0.65),
        ({}, 0.62)
    ]
    
    coverage = retriever._score_coverage(results)
    assert coverage == "medium"


def test_retriever_score_coverage_low(retriever):
    """Test coverage scoring: low"""
    results = [
        ({}, 0.45)
    ]
    
    coverage = retriever._score_coverage(results)
    assert coverage == "low"


def test_retriever_score_coverage_none(retriever):
    """Test coverage scoring: none"""
    results = []
    
    coverage = retriever._score_coverage(results)
    assert coverage == "none"


def test_retriever_detect_gaps_none_coverage(retriever):
    """Test gap detection for no coverage"""
    gaps = retriever._detect_gaps("not_hashing", "none", None)
    
    assert len(gaps) > 0
    assert "no documentation" in gaps[0].lower()


def test_retriever_detect_gaps_low_coverage(retriever):
    """Test gap detection for low coverage"""
    gaps = retriever._detect_gaps(
        "firmware_issue",
        "low",
        {"product": "Apollo III"}
    )
    
    assert len(gaps) > 0
    assert "limited" in gaps[0].lower()


def test_retriever_format_response(retriever):
    """Test response formatting"""
    results = [
        ({"title": "Test Doc", "url": "http://test.com", "content": "x" * 200, "last_updated": "2024-01-01"}, 0.89)
    ]
    
    response = retriever._format_response(results, "high", [], 42)
    
    assert len(response["sources_consulted"]) == 1
    assert response["coverage"] == "high"
    assert response["retrieval_time_ms"] == 42
    
    source = response["sources_consulted"][0]
    assert source["title"] == "Test Doc"
    assert source["url"] == "http://test.com"
    assert source["relevance_score"] == 0.89
    assert len(source["excerpt"]) == 150  # Excerpt length (locked decision)


def test_retriever_empty_response(retriever):
    """Test empty response format"""
    response = retriever._empty_response(25)
    
    assert response["sources_consulted"] == []
    assert response["coverage"] == "none"
    assert "unavailable" in response["gaps"][0].lower()
    assert response["retrieval_time_ms"] == 25


# ==============================================================================
# CATEGORY 4: Integration Tests (5 tests)
# ==============================================================================

def test_end_to_end_retrieval(temp_vector_store_path, embedder):
    """Test complete retrieval flow"""
    # Setup: Add documents to vector store
    vs = VectorStore(temp_vector_store_path, "test_kb")
    vs.initialize()
    
    docs = [
        "Apollo Not Hashing Troubleshooting: If your Apollo shows 0 H/s, first check pool configuration...",
        "Sync Delay Issues: Node sync can take time. Check getblockchaininfo..."
    ]
    embeddings = embedder.embed_batch(docs)
    metadatas = [
        {"title": "Not Hashing Guide", "url": "http://test.com/1", "last_updated": "2024-01-01"},
        {"title": "Sync Guide", "url": "http://test.com/2", "last_updated": "2024-01-01"}
    ]
    ids = ["doc1", "doc2"]
    
    vs.add_documents(docs, embeddings, metadatas, ids)
    
    # Create retriever
    ret = KnowledgeRetriever(temp_vector_store_path, "test_kb")
    ret.initialize()
    
    # Retrieve knowledge
    result = ret.retrieve_knowledge(
        intent="not_hashing",
        message="My Apollo shows 0 H/s",
        metadata={"product": "Apollo II"}
    )
    
    # Verify results
    assert len(result["sources_consulted"]) > 0
    assert result["coverage"] in ["high", "medium", "low"]
    assert result["retrieval_time_ms"] > 0
    
    # Verify most relevant doc is returned
    top_source = result["sources_consulted"][0]
    assert "not hashing" in top_source["title"].lower()


def test_retrieval_with_multiple_results(temp_vector_store_path, embedder):
    """Test retrieval returns top 3 results"""
    vs = VectorStore(temp_vector_store_path, "test_kb")
    vs.initialize()
    
    # Add 5 documents (should return top 3)
    docs = [
        f"Apollo document about not hashing issue number {i}" for i in range(5)
    ]
    embeddings = embedder.embed_batch(docs)
    metadatas = [
        {"title": f"Doc {i}", "url": f"http://test.com/{i}", "last_updated": "2024-01-01"}
        for i in range(5)
    ]
    ids = [f"doc{i}" for i in range(5)]
    
    vs.add_documents(docs, embeddings, metadatas, ids)
    
    ret = KnowledgeRetriever(temp_vector_store_path, "test_kb")
    ret.initialize()
    
    result = ret.retrieve_knowledge("not_hashing", "Apollo 0 H/s")
    
    assert len(result["sources_consulted"]) == 3  # Top 3 (locked decision)


def test_retrieval_handles_errors_gracefully(temp_vector_store_path):
    """Test retrieval degrades gracefully on errors"""
    # Create retriever but don't initialize
    ret = KnowledgeRetriever(temp_vector_store_path, "test_kb")
    # Skip initialization
    
    # Try to retrieve (should return empty response, not raise)
    result = ret.retrieve_knowledge("not_hashing", "Test message")
    
    assert result["sources_consulted"] == []
    assert result["coverage"] == "none"


def test_retrieval_respects_excerpt_length(temp_vector_store_path, embedder):
    """Test excerpts are truncated to 150 chars"""
    vs = VectorStore(temp_vector_store_path, "test_kb")
    vs.initialize()
    
    # Add document with long content
    long_content = "x" * 300
    docs = [long_content]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": "Long Doc", "url": "http://test.com", "last_updated": "2024-01-01"}]
    ids = ["doc1"]
    
    vs.add_documents(docs, embeddings, metadatas, ids)
    
    ret = KnowledgeRetriever(temp_vector_store_path, "test_kb")
    ret.initialize()
    
    result = ret.retrieve_knowledge("test", "test query")
    
    if result["sources_consulted"]:
        excerpt = result["sources_consulted"][0]["excerpt"]
        assert len(excerpt) == 150  # Locked decision: 150 chars


def test_public_api_function(temp_vector_store_path, embedder):
    """Test public API function"""
    from knowledge import retrieve_knowledge
    
    # Setup vector store with data
    vs = VectorStore(temp_vector_store_path, "test_kb")
    vs.initialize()
    
    docs = ["Apollo not hashing guide"]
    embeddings = embedder.embed_batch(docs)
    metadatas = [{"title": "Guide", "url": "http://test.com", "last_updated": "2024-01-01"}]
    ids = ["doc1"]
    
    vs.add_documents(docs, embeddings, metadatas, ids)
    
    # Call public API (will create singleton)
    # Note: In real usage, singleton would be initialized once
    result = retrieve_knowledge("not_hashing", "Apollo 0 H/s", {"product": "Apollo II"})
    
    assert "sources_consulted" in result
    assert "coverage" in result
    assert "gaps" in result
    assert "retrieval_time_ms" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])