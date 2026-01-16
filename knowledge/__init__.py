"""
Knowledge Retrieval Package
Semantic search over knowledge base documentation
"""

__version__ = "1.0.0"

# Public API exports
from .knowledge_retriever import retrieve_knowledge
from .sync import sync_knowledge_base

__all__ = [
    "retrieve_knowledge",
    "sync_knowledge_base",
]
