"""
User progress tracking routes
Track user's learning progress through the textbook
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models import UserProgress, Bookmark, Analytics
from database import get_db

router = APIRouter()


# Pydantic schemas
class ProgressUpdate(BaseModel):
    """Schema for updating progress"""
    chapter_id: str
    section_id: Optional[str] = None
    status: str  # not_started, in_progress, completed
    progress_percentage: float = 0.0
    time_spent_seconds: int = 0


class ProgressResponse(BaseModel):
    """Schema for progress response"""
    id: int
    user_id: int
    chapter_id: str
    section_id: Optional[str]
    status: str
    progress_percentage: float
    time_spent_seconds: int
    completed_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class BookmarkCreate(BaseModel):
    """Schema for creating bookmark"""
    chapter_id: str
    section_id: Optional[str] = None
    title: str
    url: str
    notes: Optional[str] = None


class BookmarkResponse(BaseModel):
    """Schema for bookmark response"""
    id: int
    user_id: int
    chapter_id: str
    section_id: Optional[str]
    title: str
    url: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/progress", response_model=ProgressResponse)
async def update_progress(
    user_id: int,
    progress_data: ProgressUpdate,
    db: Session = Depends(get_db)
):
    """
    Update user's progress for a chapter/section.

    Args:
        user_id: User's ID
        progress_data: Progress update data
        db: Database session

    Returns:
        Updated progress record
    """
    # Check if progress record exists
    existing = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.chapter_id == progress_data.chapter_id,
        UserProgress.section_id == progress_data.section_id
    ).first()

    if existing:
        # Update existing progress
        existing.status = progress_data.status
        existing.progress_percentage = progress_data.progress_percentage
        existing.time_spent_seconds += progress_data.time_spent_seconds
        existing.updated_at = datetime.utcnow()

        if progress_data.status == "completed" and not existing.completed_at:
            existing.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(existing)
        return ProgressResponse.from_orm(existing)
    else:
        # Create new progress record
        new_progress = UserProgress(
            user_id=user_id,
            chapter_id=progress_data.chapter_id,
            section_id=progress_data.section_id,
            status=progress_data.status,
            progress_percentage=progress_data.progress_percentage,
            time_spent_seconds=progress_data.time_spent_seconds,
            completed_at=datetime.utcnow() if progress_data.status == "completed" else None
        )

        db.add(new_progress)
        db.commit()
        db.refresh(new_progress)
        return ProgressResponse.from_orm(new_progress)


@router.get("/progress/{user_id}", response_model=List[ProgressResponse])
async def get_user_progress(user_id: int, db: Session = Depends(get_db)):
    """
    Get all progress records for a user.

    Args:
        user_id: User's ID
        db: Database session

    Returns:
        List of progress records
    """
    progress_records = db.query(UserProgress).filter(
        UserProgress.user_id == user_id
    ).all()

    return [ProgressResponse.from_orm(record) for record in progress_records]


@router.get("/progress/{user_id}/{chapter_id}", response_model=ProgressResponse)
async def get_chapter_progress(
    user_id: int,
    chapter_id: str,
    section_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get progress for a specific chapter/section.

    Args:
        user_id: User's ID
        chapter_id: Chapter ID
        section_id: Optional section ID
        db: Database session

    Returns:
        Progress record

    Raises:
        HTTPException: If progress record not found
    """
    progress = db.query(UserProgress).filter(
        UserProgress.user_id == user_id,
        UserProgress.chapter_id == chapter_id,
        UserProgress.section_id == section_id
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress record not found"
        )

    return ProgressResponse.from_orm(progress)


@router.post("/bookmarks", response_model=BookmarkResponse)
async def create_bookmark(
    user_id: int,
    bookmark_data: BookmarkCreate,
    db: Session = Depends(get_db)
):
    """
    Create a bookmark for a chapter/section.

    Args:
        user_id: User's ID
        bookmark_data: Bookmark data
        db: Database session

    Returns:
        Created bookmark
    """
    new_bookmark = Bookmark(
        user_id=user_id,
        chapter_id=bookmark_data.chapter_id,
        section_id=bookmark_data.section_id,
        title=bookmark_data.title,
        url=bookmark_data.url,
        notes=bookmark_data.notes
    )

    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)

    return BookmarkResponse.from_orm(new_bookmark)


@router.get("/bookmarks/{user_id}", response_model=List[BookmarkResponse])
async def get_user_bookmarks(user_id: int, db: Session = Depends(get_db)):
    """
    Get all bookmarks for a user.

    Args:
        user_id: User's ID
        db: Database session

    Returns:
        List of bookmarks
    """
    bookmarks = db.query(Bookmark).filter(
        Bookmark.user_id == user_id
    ).order_by(Bookmark.created_at.desc()).all()

    return [BookmarkResponse.from_orm(bookmark) for bookmark in bookmarks]


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    """
    Delete a bookmark.

    Args:
        bookmark_id: Bookmark ID
        db: Database session

    Raises:
        HTTPException: If bookmark not found
    """
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )

    db.delete(bookmark)
    db.commit()
    return None


@router.post("/analytics")
async def track_event(
    event_type: str,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    page_url: Optional[str] = None,
    event_data: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """
    Track analytics event.

    Args:
        event_type: Type of event (e.g., page_view, chat_query, bookmark_added)
        user_id: Optional user ID
        session_id: Optional session ID
        page_url: Optional page URL
        event_data: Optional additional event data
        db: Database session

    Returns:
        Success message
    """
    analytics_event = Analytics(
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        page_url=page_url,
        event_data=event_data
    )

    db.add(analytics_event)
    db.commit()

    return {"message": "Event tracked successfully"}


@router.get("/analytics/summary/{user_id}")
async def get_user_analytics_summary(user_id: int, db: Session = Depends(get_db)):
    """
    Get analytics summary for a user.

    Args:
        user_id: User's ID
        db: Database session

    Returns:
        Analytics summary
    """
    from sqlalchemy import func

    # Get total time spent
    total_time = db.query(func.sum(UserProgress.time_spent_seconds)).filter(
        UserProgress.user_id == user_id
    ).scalar() or 0

    # Get completed chapters count
    completed_chapters = db.query(func.count(UserProgress.id)).filter(
        UserProgress.user_id == user_id,
        UserProgress.status == "completed"
    ).scalar() or 0

    # Get in-progress chapters count
    in_progress_chapters = db.query(func.count(UserProgress.id)).filter(
        UserProgress.user_id == user_id,
        UserProgress.status == "in_progress"
    ).scalar() or 0

    # Get total bookmarks
    total_bookmarks = db.query(func.count(Bookmark.id)).filter(
        Bookmark.user_id == user_id
    ).scalar() or 0

    # Get analytics events count
    total_events = db.query(func.count(Analytics.id)).filter(
        Analytics.user_id == user_id
    ).scalar() or 0

    return {
        "total_time_spent_seconds": total_time,
        "total_time_spent_hours": round(total_time / 3600, 2),
        "completed_chapters": completed_chapters,
        "in_progress_chapters": in_progress_chapters,
        "total_bookmarks": total_bookmarks,
        "total_events": total_events
    }
