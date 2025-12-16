"""
Content routes for personalization and translation.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import (
    PersonalizeRequest,
    PersonalizeResponse,
    TranslateRequest,
    TranslateResponse,
    User,
    UserPreference,
)
from database import get_db
from services import PersonalizationService, TranslationService
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
personalization_service = PersonalizationService()
translation_service = TranslationService()


def fetch_chapter_content(chapter_id: str) -> str:
    """
    Fetch chapter content from filesystem.

    Args:
        chapter_id: Chapter identifier

    Returns:
        Chapter content as string

    Raises:
        HTTPException: If chapter not found
    """
    # Try multiple possible paths
    possible_paths = [
        Path(f"docs/{chapter_id}.md"),
        Path(f"docs/{chapter_id}/index.md"),
        Path(f"physical-ai-textbook/docs/{chapter_id}.md"),
        Path(f"physical-ai-textbook/docs/{chapter_id}/index.md"),
    ]

    for path in possible_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Chapter '{chapter_id}' not found"
    )


@router.post("/personalize", response_model=PersonalizeResponse)
async def personalize_chapter(
    request: PersonalizeRequest,
    db: Session = Depends(get_db)
):
    """
    Personalize chapter content based on user background and preferences.

    Args:
        request: Personalization request with chapter ID, user ID, and level
        db: Database session

    Returns:
        Personalized content

    Raises:
        HTTPException: If user not found or error occurs
    """
    try:
        # Get user background
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Fetch chapter content
        chapter_content = fetch_chapter_content(request.chapter_id)

        # Personalize content
        personalized = await personalization_service.personalize_content(
            content=chapter_content,
            user_background={
                "software_background": user.software_background,
                "hardware_background": user.hardware_background
            },
            level=request.level
        )

        # Save or update user preference
        pref = db.query(UserPreference).filter(
            UserPreference.user_id == request.user_id,
            UserPreference.chapter_id == request.chapter_id
        ).first()

        if pref:
            pref.personalization_level = request.level
        else:
            pref = UserPreference(
                user_id=request.user_id,
                chapter_id=request.chapter_id,
                personalization_level=request.level
            )
            db.add(pref)

        db.commit()

        logger.info(f"Content personalized for user {user.email}: {request.chapter_id} -> {request.level}")

        return PersonalizeResponse(
            personalized_content=personalized,
            level=request.level,
            chapter_id=request.chapter_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error personalizing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error personalizing content: {str(e)}"
        )


@router.post("/translate", response_model=TranslateResponse)
async def translate_chapter(
    request: TranslateRequest,
    db: Session = Depends(get_db)
):
    """
    Translate chapter content to target language.

    Args:
        request: Translation request with content and target language
        db: Database session

    Returns:
        Translated content

    Raises:
        HTTPException: If translation fails
    """
    try:
        # Translate content (with caching)
        translated = await translation_service.translate_content(
            content=request.content,
            target_lang=request.target_lang,
            db=db
        )

        logger.info(f"Content translated: {request.chapter_id} -> {request.target_lang}")

        return TranslateResponse(
            translated_content=translated,
            source_lang="en",
            target_lang=request.target_lang
        )

    except Exception as e:
        logger.error(f"Error translating content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error translating content: {str(e)}"
        )


@router.get("/chapters")
async def list_chapters():
    """
    List all available chapters.

    Returns:
        List of chapter information
    """
    # Try to find docs directory
    docs_paths = [
        Path("docs"),
        Path("physical-ai-textbook/docs")
    ]

    chapters = []
    for docs_path in docs_paths:
        if docs_path.exists():
            # Find all markdown files
            for md_file in docs_path.rglob("*.md"):
                relative_path = md_file.relative_to(docs_path)
                chapter_id = str(relative_path).replace("\\", "/").replace(".md", "")

                # Skip intro or index files at root
                if chapter_id in ["intro", "index"]:
                    continue

                chapters.append({
                    "id": chapter_id,
                    "title": chapter_id.replace("-", " ").title(),
                    "path": str(md_file)
                })
            break

    return {"chapters": chapters, "total": len(chapters)}


@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: int, db: Session = Depends(get_db)):
    """
    Get user's content preferences.

    Args:
        user_id: User's unique identifier
        db: Database session

    Returns:
        User's preferences for different chapters
    """
    preferences = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).all()

    return {
        "user_id": user_id,
        "preferences": [
            {
                "chapter_id": pref.chapter_id,
                "personalization_level": pref.personalization_level,
                "language": pref.language
            }
            for pref in preferences
        ]
    }


@router.post("/exercises/{chapter_id}")
async def generate_exercises(
    chapter_id: str,
    user_id: int,
    num_exercises: int = 3,
    db: Session = Depends(get_db)
):
    """
    Generate personalized exercises for a chapter.

    Args:
        chapter_id: Chapter identifier
        user_id: User's unique identifier
        num_exercises: Number of exercises to generate
        db: Database session

    Returns:
        List of generated exercises
    """
    try:
        # Get user background
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Fetch chapter content
        chapter_content = fetch_chapter_content(chapter_id)

        # Generate exercises
        exercises = await personalization_service.suggest_exercises(
            content=chapter_content,
            user_background={
                "software_background": user.software_background,
                "hardware_background": user.hardware_background
            },
            num_exercises=num_exercises
        )

        return {
            "chapter_id": chapter_id,
            "exercises": exercises
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating exercises: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating exercises: {str(e)}"
        )
