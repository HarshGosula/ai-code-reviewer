"""Vector store using Pinecone"""

from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
import logging
from app.config import get_settings
from app.rag.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStore:
    """Pinecone vector store for code embeddings"""
    
    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = get_embedding_service()
        
        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.settings.pinecone_api_key)
        
        # Get or create index
        self.index_name = self.settings.pinecone_index_name
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)
    
    def _ensure_index_exists(self):
        """Create index if it doesn't exist"""
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=768,  # Gemini embedding dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.settings.pinecone_environment
                )
            )
            logger.info(f"Index {self.index_name} created successfully")
    
    def upsert_code_chunks(
        self,
        repo_namespace: str,
        chunks: List[Dict[str, Any]],
    ) -> None:
        """
        Insert or update code chunks in the vector store.
        
        Args:
            repo_namespace: Repository namespace (e.g., "owner_repo")
            chunks: List of chunk dictionaries with 'id', 'text', and 'metadata'
        """
        vectors = []
        
        for chunk in chunks:
            # Generate embedding
            embedding = self.embedding_service.generate_embedding(chunk["text"])
            
            # Prepare metadata
            metadata = {
                "repo": repo_namespace,
                "text": chunk["text"][:1000],  # Store truncated text
                **chunk.get("metadata", {}),
            }
            
            vectors.append({
                "id": f"{repo_namespace}_{chunk['id']}",
                "values": embedding,
                "metadata": metadata,
            })
        
        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted batch {i // batch_size + 1} ({len(batch)} vectors)")
    
    def search(
        self,
        query: str,
        repo_namespace: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code chunks.
        
        Args:
            query: Search query
            repo_namespace: Repository namespace to search within
            top_k: Number of results to return
            filter_metadata: Additional metadata filters
            
        Returns:
            List of matching chunks with scores
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_query_embedding(query)
        
        # Build filter
        filter_dict = {"repo": {"$eq": repo_namespace}}
        if filter_metadata:
            filter_dict.update(filter_metadata)
        
        # Search
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter_dict,
            include_metadata=True,
        )
        
        # Format results
        matches = []
        for match in results.get("matches", []):
            matches.append({
                "id": match["id"],
                "score": match["score"],
                "metadata": match.get("metadata", {}),
            })
        
        return matches
    
    def delete_repository(self, repo_namespace: str) -> None:
        """
        Delete all vectors for a repository.
        
        Args:
            repo_namespace: Repository namespace
        """
        # Delete by metadata filter
        self.index.delete(filter={"repo": {"$eq": repo_namespace}})
        logger.info(f"Deleted all vectors for repository: {repo_namespace}")
    
    def get_repository_stats(self, repo_namespace: str) -> Dict[str, Any]:
        """
        Get statistics for a repository's indexed data.
        
        Args:
            repo_namespace: Repository namespace
            
        Returns:
            Statistics dictionary
        """
        stats = self.index.describe_index_stats()
        
        # Note: Pinecone doesn't provide per-namespace stats directly
        # This is a simplified version
        return {
            "total_vectors": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 768),
        }


# Singleton instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get the vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

