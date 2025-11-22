"""Embedding generation using Gemini"""

import google.generativeai as genai
from typing import List
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Gemini"""

    def __init__(self):
        self.settings = get_settings()
        genai.configure(api_key=self.settings.gemini_api_key)
        # Try newer model first, fallback to older one
        self.model_name = "models/text-embedding-004"  # Latest model
        self.fallback_model = "models/embedding-001"  # Fallback
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            # Try fallback model if primary fails
            logger.warning(f"Primary embedding model failed: {e}, trying fallback...")
            try:
                result = genai.embed_content(
                    model=self.fallback_model,
                    content=text,
                    task_type="retrieval_document",
                )
                return result["embedding"]
            except Exception as fallback_error:
                logger.error(f"Error generating embedding with fallback: {fallback_error}")
                raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for text in batch:
                try:
                    embedding = self.generate_embedding(text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Error in batch embedding: {e}")
                    # Use zero vector as fallback
                    embeddings.append([0.0] * 768)
        
        return embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a query (optimized for retrieval).

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query",
            )
            return result["embedding"]
        except Exception as e:
            # Try fallback model if primary fails
            logger.warning(f"Primary query embedding model failed: {e}, trying fallback...")
            try:
                result = genai.embed_content(
                    model=self.fallback_model,
                    content=query,
                    task_type="retrieval_query",
                )
                return result["embedding"]
            except Exception as fallback_error:
                logger.error(f"Error generating query embedding with fallback: {fallback_error}")
                raise


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get the embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

