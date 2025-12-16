"""
Chat routes for RAG-based Q&A functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import ChatRequest, ChatResponse, SelectionChatRequest
from database import get_db
from services import EmbeddingService, RAGService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services (these should ideally be dependency-injected)
embedding_service = EmbeddingService()
rag_service = RAGService(embedding_service)


@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Handle general chat queries using RAG.

    Args:
        request: Chat query request with question and optional context
        db: Database session

    Returns:
        Generated answer with source references

    Raises:
        HTTPException: If an error occurs during processing
    """
    try:
        # Retrieve context and generate answer
        answer, source_docs = await rag_service.answer_with_context(
            query=request.query,
            chapter_id=request.chapter_id,
            limit=5
        )

        # Format sources
        sources = [
            {
                "chapter": doc["chapter_title"],
                "chapter_id": doc["chapter_id"],
                "relevance": round(doc["score"], 3)
            }
            for doc in source_docs
        ]

        logger.info(f"Chat query processed: {request.query[:50]}...")

        return ChatResponse(
            response=answer,
            sources=sources
        )

    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.post("/selection", response_model=ChatResponse)
async def chat_selection(request: SelectionChatRequest):
    """
    Handle queries based on user-selected text.

    Args:
        request: Selection-based query request

    Returns:
        Generated answer based on selected text

    Raises:
        HTTPException: If an error occurs during processing
    """
    try:
        answer = await rag_service.answer_from_selection(
            selected_text=request.selected_text,
            query=request.query
        )

        logger.info(f"Selection query processed: {request.query[:50]}...")

        return ChatResponse(response=answer)

    except Exception as e:
        logger.error(f"Error processing selection query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/history/{user_id}")
async def get_chat_history(
    user_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get user's chat history (placeholder for future implementation).

    Args:
        user_id: User's unique identifier
        limit: Maximum number of messages to return
        db: Database session

    Returns:
        List of chat messages
    """
    # TODO: Implement chat history storage and retrieval
    return {
        "user_id": user_id,
        "messages": [],
        "note": "Chat history feature coming soon"
    }


@router.post("/feedback")
async def submit_feedback(
    query_id: str,
    rating: int,
    comment: str = None,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a chat response (placeholder for future implementation).

    Args:
        query_id: Unique identifier for the query
        rating: Rating from 1-5
        comment: Optional feedback comment
        db: Database session

    Returns:
        Confirmation message
    """
    # TODO: Implement feedback storage
    logger.info(f"Feedback received for query {query_id}: rating={rating}")

    return {
        "message": "Thank you for your feedback!",
        "query_id": query_id,
        "rating": rating
    }
