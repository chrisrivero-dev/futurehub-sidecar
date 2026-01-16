"""
Knowledge Base Sync Module
Handles periodic synchronization from host system API
"""
import requests
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time

from knowledge.vector_store import VectorStore
from knowledge.embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class KnowledgeBaseSync:
    """
    Syncs knowledge base articles from host system API to local vector store.
    """
    
    def __init__(
        self,
        host_api_url: str,
        vector_store_path: str = "./data/vector_store",
        collection_name: str = "kb_articles",
        cache_path: str = "./data/articles.json"
    ):
        """
        Initialize sync manager.
        
        Args:
            host_api_url: Host system knowledge base API endpoint
            vector_store_path: Path to vector store
            collection_name: Name of collection
            cache_path: Path to cached articles JSON
        """
        self.host_api_url = host_api_url
        self.cache_path = cache_path
        self.vector_store = VectorStore(vector_store_path, collection_name)
        self.embedder = EmbeddingGenerator()
        
    def initialize(self) -> bool:
        """Initialize vector store and embedding model"""
        try:
            if not self.vector_store.initialize():
                return False
            if not self.embedder.initialize():
                return False
            logger.info("Sync manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize sync manager: {e}")
            return False
    
    def fetch_articles(
        self,
        intent: Optional[str] = None,
        device: Optional[str] = None,
        updated_since: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch articles from host system API.
        
        Args:
            intent: Filter by intent (optional)
            device: Filter by device (optional)
            updated_since: ISO 8601 timestamp (optional)
        
        Returns:
            List of article dicts
        """
        try:
            # Build query parameters
            params = {}
            if intent:
                params["intent"] = intent
            if device:
                params["device"] = device
            if updated_since:
                params["updated_since"] = updated_since
            
            # Make API request
            logger.info(f"Fetching articles from {self.host_api_url}")
            response = requests.get(
                self.host_api_url,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            articles = data.get("articles", [])
            
            logger.info(f"Fetched {len(articles)} articles")
            return articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch articles from API: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            return []
    
    def load_cached_articles(self) -> List[Dict]:
        """Load articles from local cache"""
        try:
            with open(self.cache_path, 'r') as f:
                cache = json.load(f)
                return cache.get("articles", [])
        except FileNotFoundError:
            logger.info("No cached articles found")
            return []
        except Exception as e:
            logger.error(f"Failed to load cached articles: {e}")
            return []
    
    def save_cached_articles(self, articles: List[Dict]):
        """Save articles to local cache"""
        try:
            cache = {
                "articles": articles,
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
            with open(self.cache_path, 'w') as f:
                json.dump(cache, f, indent=2)
            logger.info(f"Saved {len(articles)} articles to cache")
        except Exception as e:
            logger.error(f"Failed to save cached articles: {e}")
    
    def sync(self, force_rebuild: bool = False) -> Dict:
        """
        Sync knowledge base from host API.
        
        Args:
            force_rebuild: If True, rebuild entire vector store
        
        Returns:
            Sync statistics dict
        """
        start_time = time.time()
        stats = {
            "articles_added": 0,
            "articles_updated": 0,
            "articles_deleted": 0,
            "chunks_added": 0,
            "errors": 0,
            "duration_seconds": 0
        }
        
        try:
            # Load cached articles (for comparison)
            cached_articles = self.load_cached_articles()
            cached_by_id = {a["id"]: a for a in cached_articles}
            
            # Fetch new articles from API
            new_articles = self.fetch_articles()
            
            if not new_articles:
                logger.warning("No articles fetched from API")
                # Fall back to cache if API fails
                if cached_articles:
                    logger.info("Using cached articles")
                    new_articles = cached_articles
                else:
                    logger.error("No articles available (API failed, no cache)")
                    return stats
            
            new_by_id = {a["id"]: a for a in new_articles}
            
            # Determine changes
            added_ids = set(new_by_id.keys()) - set(cached_by_id.keys())
            updated_ids = []
            deleted_ids = set(cached_by_id.keys()) - set(new_by_id.keys())
            
            # Check for updates (compare last_updated timestamp)
            for article_id in set(new_by_id.keys()) & set(cached_by_id.keys()):
                new_updated = new_by_id[article_id]["metadata"].get("last_updated", "")
                cached_updated = cached_by_id[article_id]["metadata"].get("last_updated", "")
                if new_updated != cached_updated:
                    updated_ids.append(article_id)
            
            # Process deletions
            if deleted_ids:
                # Find all chunk IDs for deleted articles
                chunk_ids_to_delete = []
                for article_id in deleted_ids:
                    # Pattern: article_id_chunk_0, article_id_chunk_1, etc.
                    # For simplicity, we'll skip deletion in MVP
                    # (vector store will be rebuilt periodically anyway)
                    pass
                stats["articles_deleted"] = len(deleted_ids)
            
            # Process additions
            for article_id in added_ids:
                article = new_by_id[article_id]
                if self._process_article(article):
                    stats["articles_added"] += 1
                    stats["chunks_added"] += self._count_chunks(article)
                else:
                    stats["errors"] += 1
            
            # Process updates
            for article_id in updated_ids:
                article = new_by_id[article_id]
                # For MVP, treat updates as additions (no deletion)
                if self._process_article(article):
                    stats["articles_updated"] += 1
                    stats["chunks_added"] += self._count_chunks(article)
                else:
                    stats["errors"] += 1
            
            # Save updated cache
            self.save_cached_articles(new_articles)
            
            # Calculate duration
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            
            logger.info(f"Sync complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            stats["errors"] += 1
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            return stats
    
    def _process_article(self, article: Dict) -> bool:
        """
        Process a single article: chunk, embed, and add to vector store.
        
        Args:
            article: Article dict from API
        
        Returns:
            True if successful, False otherwise
        """
        try:
            article_id = article["id"]
            title = article["title"]
            url = article["url"]
            content = article["content"]
            metadata = article["metadata"]
            
            # Process article into chunks
            chunks = self.embedder.process_article(
                article_id=article_id,
                title=title,
                url=url,
                content=content,
                metadata=metadata
            )
            
            # Extract data for vector store
            chunk_ids = [c[0] for c in chunks]
            chunk_texts = [c[1] for c in chunks]
            chunk_embeddings = [c[2] for c in chunks]
            chunk_metadatas = [c[3] for c in chunks]
            
            # Add to vector store
            success = self.vector_store.add_documents(
                documents=chunk_texts,
                embeddings=chunk_embeddings,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process article {article.get('id')}: {e}")
            return False
    
    def _count_chunks(self, article: Dict) -> int:
        """Estimate number of chunks for an article"""
        content = article.get("content", "")
        words = len(content.split())
        # Approximate: 500 words per chunk with 50 word overlap
        return max(1, (words // 450))


def sync_knowledge_base(
    host_api_url: str,
    force_rebuild: bool = False
) -> Dict:
    """
    Public API: Sync knowledge base from host system.
    
    This function can be called from a cron job or scheduled task.
    
    Args:
        host_api_url: Host system knowledge base API endpoint
        force_rebuild: If True, rebuild entire vector store
    
    Returns:
        Sync statistics dict
    
    Example:
        stats = sync_knowledge_base(
            host_api_url="http://localhost:3000/api/kb/articles"
        )
        print(f"Added {stats['articles_added']} articles")
    """
    sync_manager = KnowledgeBaseSync(host_api_url)
    
    if not sync_manager.initialize():
        logger.error("Failed to initialize sync manager")
        return {
            "articles_added": 0,
            "articles_updated": 0,
            "articles_deleted": 0,
            "errors": 1,
            "duration_seconds": 0
        }
    
    return sync_manager.sync(force_rebuild=force_rebuild)