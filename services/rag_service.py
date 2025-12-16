"""
RAG (Retrieval-Augmented Generation) service for intelligent responses.
"""
from openai import OpenAI
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG-based question answering."""

    def __init__(self, embedding_service):
        """
        Initialize RAG service.

        Args:
            embedding_service: Instance of EmbeddingService for retrieval
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_service = embedding_service
        self.model = "gpt-4o-mini"

    async def generate_response(
        self,
        query: str,
        context_docs: List[Dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate response using RAG approach.

        Args:
            query: User's question
            context_docs: Retrieved relevant documents
            system_prompt: Optional custom system prompt
            temperature: Model temperature
            max_tokens: Maximum tokens in response

        Returns:
            Generated response
        """
        # Build context from retrieved documents
        context_parts = []
        for idx, doc in enumerate(context_docs, 1):
            context_parts.append(
                f"[Source {idx}: {doc['chapter_title']}]\n{doc['text']}"
            )

        context = "\n\n".join(context_parts)

        # Default system prompt
        if not system_prompt:
            system_prompt = """You are an expert AI tutor teaching Physical AI and Humanoid Robotics.

Your role is to:
- Answer questions based on the provided context from the textbook
- Be clear, concise, and educational
- Use examples to illustrate complex concepts
- If the context doesn't contain enough information, acknowledge this and provide what you can
- Maintain a friendly, encouraging tone suitable for students

When answering:
1. Focus on the most relevant information from the context
2. Break down complex topics into understandable parts
3. Reference specific concepts from the textbook when applicable
4. Encourage further learning and exploration"""

        try:
            # Generate response using OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context from textbook:\n\n{context}\n\nStudent's question: {query}"
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            answer = response.choices[0].message.content
            logger.info(f"Generated response for query: {query[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    async def answer_from_selection(
        self,
        selected_text: str,
        query: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Answer question based on user-selected text.

        Args:
            selected_text: Text selected by user
            query: User's question about the selection
            temperature: Model temperature
            max_tokens: Maximum tokens in response

        Returns:
            Generated answer
        """
        system_prompt = """You are an expert AI tutor helping students understand specific passages from a textbook on Physical AI and Humanoid Robotics.

Your role is to:
- Answer questions based ONLY on the selected text provided
- Be concise and precise
- Clarify concepts that might be confusing
- Provide examples when helpful
- If the question cannot be answered from the selection, say so clearly

Keep your answers focused and to the point."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Selected text:\n\n{selected_text}\n\nQuestion: {query}"
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            answer = response.choices[0].message.content
            logger.info(f"Generated answer for selection query: {query[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"Error answering from selection: {str(e)}")
            raise

    async def answer_with_context(
        self,
        query: str,
        chapter_id: Optional[str] = None,
        limit: int = 5
    ) -> tuple[str, List[Dict]]:
        """
        Answer question by retrieving context and generating response.

        Args:
            query: User's question
            chapter_id: Optional chapter to limit search
            limit: Number of context chunks to retrieve

        Returns:
            Tuple of (answer, source documents)
        """
        # Retrieve relevant context
        context_docs = await self.embedding_service.search_similar(
            query=query,
            limit=limit,
            chapter_id=chapter_id
        )

        if not context_docs:
            return (
                "I couldn't find relevant information in the textbook to answer your question. "
                "Could you please rephrase or ask about a different topic?",
                []
            )

        # Generate response
        answer = await self.generate_response(
            query=query,
            context_docs=context_docs
        )

        return answer, context_docs

    async def generate_summary(
        self,
        content: str,
        max_length: int = 200
    ) -> str:
        """
        Generate a summary of content.

        Args:
            content: Content to summarize
            max_length: Maximum length of summary in words

        Returns:
            Summary text
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Summarize the following text in approximately {max_length} words. "
                                   "Focus on key concepts and main ideas."
                    },
                    {"role": "user", "content": content}
                ],
                temperature=0.5,
                max_tokens=max_length * 2  # Rough estimate
            )

            summary = response.choices[0].message.content
            logger.info("Generated content summary")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            raise
