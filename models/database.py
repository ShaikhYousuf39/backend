"""
Database models for Physical AI Textbook.
Consolidated SQLAlchemy models for authentication, progress, bookmarks, chat history, preferences, analytics, and translation cache.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    software_background = Column(String(50), nullable=True)
    hardware_background = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"


class UserSession(Base):
    """Active user sessions for token management."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, index=True, nullable=False)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession user_id={self.user_id} active={self.is_active}>"


class UserProgress(Base):
    """Track user progress through textbook chapters."""
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(100), nullable=False)
    section_id = Column(String(100), nullable=True)
    status = Column(String(20), default="not_started")
    progress_percentage = Column(Float, default=0.0)
    time_spent_seconds = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="progress")

    def __repr__(self):
        return f"<UserProgress user_id={self.user_id} chapter={self.chapter_id} status={self.status}>"


class Bookmark(Base):
    """User bookmarks for saving important sections."""
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(100), nullable=False)
    section_id = Column(String(100), nullable=True)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")

    def __repr__(self):
        return f"<Bookmark user_id={self.user_id} title={self.title}>"


class ChatHistory(Base):
    """Store user chat interactions with the RAG chatbot."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String(100), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    model_used = Column(String(50), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_history")

    def __repr__(self):
        return f"<ChatHistory session_id={self.session_id} role={self.role}>"


class UserPreference(Base):
    """User preferences and settings."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    language = Column(String(10), default="en")
    theme = Column(String(20), default="light")
    notifications_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=False)
    auto_translate = Column(Boolean, default=False)
    preferred_difficulty = Column(String(20), default="intermediate")
    settings_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreference user_id={self.user_id} language={self.language}>"


class Analytics(Base):
    """Track usage analytics and metrics."""
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(100), nullable=True)
    page_url = Column(String(500), nullable=True)
    event_data = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Analytics event={self.event_type} at={self.created_at}>"


class TranslationCache(Base):
    """Cache for translated content to reduce API calls."""
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content_hash = Column(String(255), unique=True, nullable=False, index=True)
    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    translated_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
