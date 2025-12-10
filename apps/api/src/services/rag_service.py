"""
RAG Service

Vector search and retrieval-augmented generation with Qdrant
"""
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct

from src.core.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """RAG operations with Qdrant vector database"""
    
    def __init__(self):
        """Initialize Qdrant client and embeddings"""
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.embedding_dim = settings.EMBEDDING_DIM
        
        # Ensure collection exists
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
    
    async def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings from Ollama
        
        TODO: Move to separate EmbeddingService
        """
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                    json={
                        "model": settings.EMBEDDING_MODEL,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result["embedding"]
                
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant documents using vector similarity
        
        Args:
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_metadata: Optional metadata filters
            
        Returns:
            List of documents with metadata and scores
        """
        try:
            # Get query embeddings
            query_vector = await self.get_embeddings(query)
            
            # Build filter if metadata provided
            search_filter = None
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
                search_filter = models.Filter(must=conditions)
            
            # Search in Qdrant
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter,
                with_payload=True
            )
            
            # Format results
            results = []
            for hit in search_results:
                results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.payload.get("content", ""),
                    "title": hit.payload.get("title", "Untitled"),
                    "source": hit.payload.get("source", "Unknown"),
                    "metadata": hit.payload.get("metadata", {}),
                    "created_at": hit.payload.get("created_at"),
                })
            
            logger.info(f"Found {len(results)} documents for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    async def add_document(
        self,
        content: str,
        metadata: Dict,
        title: Optional[str] = None,
        source: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Add document to vector store
        
        Args:
            content: Document text content
            metadata: Additional metadata
            title: Document title
            source: Document source/origin
            user_id: User who uploaded the document
            
        Returns:
            Document ID
        """
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Get embeddings
            embeddings = await self.get_embeddings(content)
            
            # Prepare payload
            payload = {
                "content": content,
                "title": title or "Untitled",
                "source": source or "Unknown",
                "metadata": metadata,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            # Add to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=doc_id,
                        vector=embeddings,
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"Added document {doc_id} to collection")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise
    
    async def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        Get document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id],
                with_payload=True,
                with_vectors=False
            )
            
            if not result:
                return None
            
            point = result[0]
            return {
                "id": point.id,
                "content": point.payload.get("content", ""),
                "title": point.payload.get("title", "Untitled"),
                "source": point.payload.get("source", "Unknown"),
                "metadata": point.payload.get("metadata", {}),
                "user_id": point.payload.get("user_id"),
                "created_at": point.payload.get("created_at"),
            }
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
    
    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[doc_id]
                )
            )
            logger.info(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    async def list_collections(self) -> List[Dict]:
        """
        List all available collections
        
        Returns:
            List of collection info
        """
        try:
            collections = self.client.get_collections().collections
            
            result = []
            for col in collections:
                # Get collection info
                info = self.client.get_collection(col.name)
                result.append({
                    "name": col.name,
                    "count": info.points_count,
                    "vectors_count": info.vectors_count,
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    async def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict:
        """
        Get statistics for a collection
        
        Args:
            collection_name: Collection name (default: current collection)
            
        Returns:
            Collection statistics
        """
        try:
            col_name = collection_name or self.collection_name
            info = self.client.get_collection(col_name)
            
            return {
                "name": col_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status,
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {}
