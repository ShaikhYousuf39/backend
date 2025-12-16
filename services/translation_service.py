"""
Translation service with caching for cost efficiency.
"""
from openai import OpenAI
import os
import hashlib
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for translating content with caching."""

    def __init__(self):
        """Initialize OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.openai_client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def _get_content_hash(self, content: str, target_lang: str) -> str:
        """
        Generate hash for content caching.

        Args:
            content: Content to hash
            target_lang: Target language

        Returns:
            MD5 hash string
        """
        hash_input = f"{content}_{target_lang}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    async def translate_content(
        self,
        content: str,
        target_lang: str,
        db: Session,
        source_lang: str = "en"
    ) -> str:
        """
        Translate content with caching to reduce API calls.

        Args:
            content: Content to translate
            target_lang: Target language code (en, ur)
            db: Database session
            source_lang: Source language code

        Returns:
            Translated content
        """
        from models.database import TranslationCache

        # Check cache first
        content_hash = self._get_content_hash(content, target_lang)
        cached = db.query(TranslationCache).filter(
            TranslationCache.content_hash == content_hash
        ).first()

        if cached:
            logger.info(f"Translation found in cache: {content_hash[:8]}...")
            return cached.translated_content

        # Determine language name
        lang_map = {
            "en": "English",
            "ur": "Urdu"
        }
        target_lang_name = lang_map.get(target_lang, target_lang)

        # Translate using OpenAI
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a professional translator specializing in technical and educational content about Physical AI and Humanoid Robotics.

Translate the following content to {target_lang_name}:
- Maintain technical accuracy
- Keep technical terms in English when appropriate (e.g., "Physical AI", "robotics", "actuator")
- Preserve formatting (markdown, code blocks, etc.)
- Ensure the translation is natural and readable
- Maintain the educational tone"""
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=4000
            )

            translated = response.choices[0].message.content

            # Cache the result
            cache_entry = TranslationCache(
                content_hash=content_hash,
                source_lang=source_lang,
                target_lang=target_lang,
                translated_content=translated
            )
            db.add(cache_entry)
            db.commit()

            logger.info(f"Content translated and cached: {target_lang}")
            return translated

        except Exception as e:
            logger.error(f"Error translating content: {str(e)}")
            raise

    async def translate_batch(
        self,
        contents: list[str],
        target_lang: str,
        db: Session
    ) -> list[str]:
        """
        Translate multiple content pieces efficiently.

        Args:
            contents: List of content strings to translate
            target_lang: Target language code
            db: Database session

        Returns:
            List of translated content
        """
        translations = []

        for content in contents:
            translated = await self.translate_content(
                content=content,
                target_lang=target_lang,
                db=db
            )
            translations.append(translated)

        return translations

    def get_supported_languages(self) -> dict:
        """
        Get list of supported languages.

        Returns:
            Dictionary of language codes and names
        """
        return {
            "en": "English",
            "ur": "Urdu"
        }

    def clear_cache(self, db: Session, older_than_days: int = 30) -> int:
        """
        Clear old translations from cache.

        Args:
            db: Database session
            older_than_days: Remove translations older than this

        Returns:
            Number of entries removed
        """
        from models.database import TranslationCache
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        deleted = db.query(TranslationCache).filter(
            TranslationCache.created_at < cutoff_date
        ).delete()

        db.commit()
        logger.info(f"Cleared {deleted} old translation cache entries")
        return deleted
