"""
Embedding service for content vectorization and semantic search.
"""
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os
import hashlib
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for embedding content and performing semantic search."""

    def __init__(self):
        """Initialize OpenAI and Qdrant clients."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Initialize OpenAI client with explicit parameters
        self.openai_client = OpenAI(
            api_key=api_key,
            timeout=60.0,
            max_retries=2
        )

        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable not set")

        # Initialize Qdrant client with proper parameters
        if qdrant_key:
            self.qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_key,
                timeout=60
            )
        else:
            self.qdrant_client = QdrantClient(
                url=qdrant_url,
                timeout=60
            )

        self.collection_name = "book_content"
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimension = 1536

        self._ensure_collection()

    def _ensure_collection(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            self.qdrant_client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.info(f"Creating collection '{self.collection_name}'")
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Collection '{self.collection_name}' created successfully")

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better context preservation.

        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk.rfind('. ')
                if last_period > chunk_size // 2:
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - overlap if end < text_length else text_length

        return chunks

    async def embed_content(self, content: str, metadata: Dict) -> int:
        """
        Embed content and store in Qdrant vector database.

        Args:
            content: Text content to embed
            metadata: Metadata about the content (chapter_id, chapter_title)

        Returns:
            Number of chunks created
        """
        chunks = self.chunk_text(content)
        logger.info(f"Embedding {len(chunks)} chunks for chapter: {metadata.get('chapter_title')}")

        for idx, chunk in enumerate(chunks):
            try:
                # Generate embedding using OpenAI
                embedding_response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=chunk
                )
                embedding = embedding_response.data[0].embedding

                # Create unique ID for the chunk
                content_id = hashlib.md5(
                    f"{metadata['chapter_id']}_{idx}".encode()
                ).hexdigest()

                # Store in Qdrant
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        PointStruct(
                            id=content_id,
                            vector=embedding,
                            payload={
                                "text": chunk,
                                "chapter_id": metadata["chapter_id"],
                                "chapter_title": metadata["chapter_title"],
                                "chunk_index": idx,
                                "total_chunks": len(chunks)
                            }
                        )
                    ]
                )

                logger.debug(f"Embedded chunk {idx + 1}/{len(chunks)}")

            except Exception as e:
                logger.error(f"Error embedding chunk {idx}: {str(e)}")
                raise

        logger.info(f"Successfully embedded {len(chunks)} chunks")
        return len(chunks)

    async def search_similar(self, query: str, limit: int = 5, chapter_id: Optional[str] = None) -> List[Dict]:
        """
        Search for similar content using semantic search.

        Args:
            query: Search query
            limit: Maximum number of results
            chapter_id: Optional chapter ID to filter results

        Returns:
            List of similar content chunks with metadata
        """
        try:
            # Embed the query
            query_embedding = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=query
            ).data[0].embedding

            # Build filter if chapter_id provided
            search_filter = None
            if chapter_id:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="chapter_id",
                            match=MatchValue(value=chapter_id)
                        )
                    ]
                )

            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter
            )

            results = []
            for hit in search_results:
                results.append({
                    "text": hit.payload["text"],
                    "chapter_id": hit.payload["chapter_id"],
                    "chapter_title": hit.payload["chapter_title"],
                    "chunk_index": hit.payload.get("chunk_index", 0),
                    "score": hit.score
                })

            logger.info(f"Found {len(results)} similar chunks for query")
            return results

        except Exception as e:
            logger.error(f"Error searching similar content: {str(e)}")
            raise

    def delete_chapter_embeddings(self, chapter_id: str) -> bool:
        """
        Delete all embeddings for a specific chapter.

        Args:
            chapter_id: Chapter ID to delete

        Returns:
            Success status
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="chapter_id",
                            match=MatchValue(value=chapter_id)
                        )
                    ]
                )
            )
            logger.info(f"Deleted embeddings for chapter: {chapter_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chapter embeddings: {str(e)}")
            return False
