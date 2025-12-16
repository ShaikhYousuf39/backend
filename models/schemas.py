"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = Field(default=None, max_length=255)
    software_background: Optional[str] = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    hardware_background: Optional[str] = Field(default=None, pattern="^(none|basic|intermediate|advanced)$")


class UserResponse(BaseModel):
    """Schema for user data response."""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    software_background: Optional[str] = None
    hardware_background: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserSignIn(BaseModel):
    """Schema for user sign-in."""
    email: EmailStr
    password: str


class ChatRequest(BaseModel):
    """Schema for general chat queries."""
    query: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[int] = None
    chapter_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema for chat responses."""
    response: str
    sources: List[dict] = []


class SelectionChatRequest(BaseModel):
    """Schema for text selection-based queries."""
    selected_text: str = Field(..., min_length=10, max_length=5000)
    query: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[int] = None


class PersonalizeRequest(BaseModel):
    """Schema for content personalization."""
    chapter_id: str
    user_id: int
    level: str = Field(..., pattern="^(simplified|standard|advanced)$")


class PersonalizeResponse(BaseModel):
    """Schema for personalization response."""
    personalized_content: str
    level: str
    chapter_id: str


class TranslateRequest(BaseModel):
    """Schema for translation requests."""
    chapter_id: str
    content: str = Field(..., min_length=1)
    target_lang: str = Field(..., pattern="^(en|ur)$")


class TranslateResponse(BaseModel):
    """Schema for translation response."""
    translated_content: str
    source_lang: str
    target_lang: str


class HealthCheck(BaseModel):
    """Schema for health check response."""
    status: str
    message: str
    timestamp: datetime
