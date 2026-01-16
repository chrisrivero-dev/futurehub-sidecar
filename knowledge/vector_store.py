"""
Vector Store Interface (ChromaDB)
Manages document embeddings and semantic search
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Interface for ChromaDB vector store.
    
    Handles document storage, search, and lifecycle management.
    """
    
    def __init__(self, path: str = "./data/vector_store", collection_name: str = "kb_articles"):
        """
        Initialize vector store.
        
        Args:
            path: Path to ChromaDB storage directory
            collection_name: Name of the collection
        """
        self.path = path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
    def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            self.client = chromadb.PersistentClient(
                path=self.path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Cosine similarity
            )
            
            logger.info(f"Vector store initialized: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return False
    
    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        ids: List[str]
    ) -> bool:
        """
        Add documents to vector store.
        
        Args:
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: List of unique document IDs
        
        Returns:
            True if successful, False otherwise
        """
        if not self.collection:
            logger.error("Vector store not initialized")
            return False
        
        try:
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        threshold: float = 0.7,
        filters: Optional[Dict] = None
    ) -> List[Tuple[Dict, float]]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            threshold: Minimum similarity score (0.0-1.0)
            filters: Optional metadata filters
        
        Returns:
            List of (metadata, score) tuples
        """
        if not self.collection:
            logger.error("Vector store not initialized")
            return []
        
        try:
            # Query vector store
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # Fetch extra for filtering
                where=filters
            )
            
            # Extract results
            documents = results["documents"][0] if results["documents"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []
            
            # Convert distances to similarity scores (cosine distance → similarity)
            # ChromaDB returns distances, we want similarity (1 - distance)
            similarities = [1.0 - dist for dist in distances]
            
            # Filter by threshold and format results
            filtered_results = []
            for doc, meta, score in zip(documents, metadatas, similarities):
                if score >= threshold:
                    # Add document text to metadata for convenience
                    meta["content"] = doc
                    filtered_results.append((meta, score))
            
            # Return top_k results
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents from vector store.
        
        Args:
            ids: List of document IDs to delete
        
        Returns:
            True if successful, False otherwise
        """
        if not self.collection:
            logger.error("Vector store not initialized")
            return False
        
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    def update_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict]
    ) -> bool:
        """
        Update existing documents.
        
        Args:
            ids: List of document IDs to update
            documents: New document texts
            embeddings: New embedding vectors
            metadatas: New metadata dicts
        
        Returns:
            True if successful, False otherwise
        """
        if not self.collection:
            logger.error("Vector store not initialized")
            return False
        
        try:
            self.collection.update(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Updated {len(ids)} documents in vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update documents: {e}")
            return False
    
    def get_count(self) -> int:
        """Get total number of documents in collection"""
        if not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0
    
    def reset(self) -> bool:
        """Delete all documents from collection (for testing)"""
        if not self.collection:
            return False
        
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Vector store reset")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            return False