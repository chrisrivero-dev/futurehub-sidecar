"""
Knowledge Retrieval Module
Main interface for semantic search over knowledge base
"""
from typing import Dict, List, Optional
import logging
import time

from knowledge.vector_store import VectorStore
from knowledge.embeddings import EmbeddingGenerator, extract_keywords

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """
    Main knowledge retrieval interface.
    
    Handles query formation, semantic search, and response formatting.
    """
    
    def __init__(
        self,
        vector_store_path: str = "./data/vector_store",
        collection_name: str = "kb_articles",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize knowledge retriever.
        
        Args:
            vector_store_path: Path to ChromaDB storage
            collection_name: Name of the collection
            model_name: Embedding model name
        """
        self.vector_store = VectorStore(vector_store_path, collection_name)
        self.embedder = EmbeddingGenerator(model_name)
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize vector store and embedding model"""
        try:
            # Initialize vector store
            if not self.vector_store.initialize():
                logger.error("Failed to initialize vector store")
                return False
            
            # Initialize embedding model
            if not self.embedder.initialize():
                logger.error("Failed to initialize embedding model")
                return False
            
            self.initialized = True
            logger.info("Knowledge retriever initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge retriever: {e}")
            return False
    
    def retrieve_knowledge(
        self,
        intent: str,
        message: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Retrieve relevant knowledge for a support query.
        
        Args:
            intent: Primary intent from classification
            message: Customer's latest message
            metadata: Optional metadata (product, attachments, etc.)
        
        Returns:
            dict with sources_consulted, coverage, gaps, retrieval_time_ms
        """
        start_time = time.perf_counter()
        
        # Check initialization
        if not self.initialized:
            logger.warning("Knowledge retriever not initialized")
            return self._empty_response(0)
        
        try:
            # Step 1: Form query
            query = self._form_query(intent, message, metadata)
            logger.debug(f"Formed query: {query}")
            
            # Step 2: Generate query embedding
            query_embedding = self.embedder.embed_text(query)
            
            # Step 3: Build metadata filters
            filters = self._build_filters(intent, metadata)
            
            # Step 4: Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=3,  # Top 3 sources (locked decision)
                threshold=0.7,
                filters=filters
            )
            
            # Step 5: Score coverage
            coverage = self._score_coverage(results)
            
            # Step 6: Detect gaps (if any)
            gaps = self._detect_gaps(intent, coverage, metadata)
            
            # Step 7: Format response
            end_time = time.perf_counter()
            retrieval_time_ms = int((end_time - start_time) * 1000)
            
            return self._format_response(results, coverage, gaps, retrieval_time_ms)
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            end_time = time.perf_counter()
            retrieval_time_ms = int((end_time - start_time) * 1000)
            return self._empty_response(retrieval_time_ms)
    
    def _form_query(self, intent: str, message: str, metadata: Optional[Dict]) -> str:
        """
        Form semantic search query from intent and message.
        
        Examples:
        - intent="not_hashing", message="0 H/s" → "Apollo not hashing 0 H/s"
        - intent="sync_delay", message="stuck at block" → "Apollo sync stuck"
        """
        # Extract device from metadata
        device = "Apollo"
        if metadata and "product" in metadata:
            product = metadata["product"]
            if "apollo iii" in product.lower() or "apollo3" in product.lower():
                device = "Apollo III"
            elif "apollo ii" in product.lower() or "apollo2" in product.lower():
                device = "Apollo II"
            elif "solo node" in product.lower():
                device = "Solo Node"
        
        # Extract keywords from message
        keywords = extract_keywords(message, max_keywords=3)
        
        # Build query: device + intent + keywords
        query_parts = [device, intent.replace("_", " ")]
        query_parts.extend(keywords)
        
        query = " ".join(query_parts)
        return query
    
    def _build_filters(self, intent: str, metadata: Optional[Dict]) -> Optional[Dict]:
        """
        Build metadata filters for search.
        
        Filters by:
        - Intent (must match)
        - Device (if specified)
        """
        filters = {}
        
        # Note: ChromaDB filtering requires exact schema match
        # For MVP, we'll handle filtering in post-processing
        # Advanced filtering can be added in Phase 4B
        
        return None  # No filters for MVP (filter in post-processing)
    
    def _score_coverage(self, results: List) -> str:
        """
        Score how well knowledge base covers the query.
        
        Rules (locked decisions):
        - high: 3+ results with score ≥ 0.75
        - medium: 1-2 results with score ≥ 0.6
        - low: 1+ results with score ≥ 0.4
        - none: 0 results or all scores < 0.4
        """
        if not results:
            return "none"
        
        # Count results by threshold
        high_quality = [r for r in results if r[1] >= 0.75]
        medium_quality = [r for r in results if r[1] >= 0.6]
        low_quality = [r for r in results if r[1] >= 0.4]
        
        if len(high_quality) >= 3:
            return "high"
        elif len(medium_quality) >= 1:
            return "medium"
        elif len(low_quality) >= 1:
            return "low"
        else:
            return "none"
    
    def _detect_gaps(
        self,
        intent: str,
        coverage: str,
        metadata: Optional[Dict]
    ) -> List[str]:
        """
        Detect gaps in knowledge base coverage.
        
        For MVP: Simple heuristic based on coverage score.
        Phase 4A.3: More sophisticated gap detection.
        """
        gaps = []
        
        if coverage == "none":
            gaps.append(f"No documentation found for {intent}")
        elif coverage == "low":
            device = metadata.get("product", "Apollo") if metadata else "Apollo"
            gaps.append(f"Limited {device} documentation for {intent}")
        
        return gaps
    
    def _format_response(
        self,
        results: List,
        coverage: str,
        gaps: List[str],
        retrieval_time_ms: int
    ) -> Dict:
        """
        Format knowledge retrieval response.
        
        Returns v1.1 compatible response with sources.
        """
        sources = []
        
        for metadata, score in results[:3]:  # Top 3 (locked decision)
            # Extract excerpt (first 150 chars)
            content = metadata.get("content", "")
            excerpt = content[:150] if len(content) > 150 else content
            
            sources.append({
                "title": metadata.get("title", "Unknown"),
                "url": metadata.get("url", ""),
                "relevance_score": round(score, 2),
                "excerpt": excerpt,
                "last_updated": metadata.get("last_updated", "")
            })
        
        return {
            "sources_consulted": sources,
            "coverage": coverage,
            "gaps": gaps,
            "retrieval_time_ms": retrieval_time_ms
        }
    
    def _empty_response(self, retrieval_time_ms: int) -> Dict:
        """
        Return empty response (v1.0 fallback).
        
        Used when retrieval fails or no results found.
        """
        return {
            "sources_consulted": [],
            "coverage": "none",
            "gaps": ["Knowledge retrieval unavailable"],
            "retrieval_time_ms": retrieval_time_ms
        }


# Public API function (for easy import in app_v1.py)
_retriever_instance = None


def get_retriever() -> KnowledgeRetriever:
    """Get or create singleton knowledge retriever instance"""
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
        _retriever_instance.initialize()
    
    return _retriever_instance


def retrieve_knowledge(intent: str, message: str, metadata: Optional[Dict] = None) -> Dict:
    """
    Public API: Retrieve relevant knowledge for a support query.
    
    This is the main function that will be called from app_v1.py in Phase 4A.2.
    
    Args:
        intent: Primary intent from classification
        message: Customer's latest message
        metadata: Optional metadata dict
    
    Returns:
        dict with sources_consulted, coverage, gaps, retrieval_time_ms
    
    Example:
        knowledge = retrieve_knowledge(
            intent="not_hashing",
            message="My Apollo shows 0 H/s",
            metadata={"product": "Apollo II"}
        )
    """
    try:
        retriever = get_retriever()
        return retriever.retrieve_knowledge(intent, message, metadata)
    except Exception as e:
        logger.error(f"Knowledge retrieval failed: {e}")
        return {
            "sources_consulted": [],
            "coverage": "none",
            "gaps": ["Knowledge retrieval unavailable"],
            "retrieval_time_ms": 0
        }