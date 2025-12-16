"""
Authentication routes for user signup and signin.
Uses PostgreSQL database for user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import hashlib
import secrets
import logging
from typing import Optional

# Import database models and session
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models import User, UserSession, UserPreference
from database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas for request/response validation
class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    software_background: Optional[str] = None
    hardware_background: Optional[str] = None


class UserSignIn(BaseModel):
    """Schema for user sign-in"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (without password)"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    software_background: Optional[str] = None
    hardware_background: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    token_type: str
    user: UserResponse


# Password hashing functions (SHA256 for Python 3.13 compatibility)
def hash_password(password: str) -> str:
    """Hash password using SHA256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        salt, hash_val = hashed_password.split(":")
        return hashlib.sha256((salt + plain_password).encode()).hexdigest() == hash_val
    except:
        return False


def generate_token() -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(32)


def get_client_info(request: Request) -> tuple:
    """Extract client IP and user agent from request"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")[:500]
    return ip_address, user_agent


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        user_data: User registration data (email, username, password)
        request: FastAPI request object
        db: Database session

    Returns:
        Access token and user data

    Raises:
        HTTPException: If email or username already exists
    """
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Hash password
    hashed_password = hash_password(user_data.password)

    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        software_background=user_data.software_background,
        hardware_background=user_data.hardware_background,
        is_active=True,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create default user preferences
    preferences = UserPreference(
        user_id=new_user.id,
        language="en",
        theme="light",
        notifications_enabled=True
    )
    db.add(preferences)

    # Create session token
    token = generate_token()
    ip_address, user_agent = get_client_info(request)

    session = UserSession(
        user_id=new_user.id,
        token=token,
        device_info=user_agent,
        ip_address=ip_address,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()

    logger.info(f"New user registered: {new_user.email}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(new_user)
    )


@router.post("/signin", response_model=TokenResponse)
async def signin(credentials: UserSignIn, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate user and create session.

    Args:
        credentials: User sign-in credentials (email, password)
        request: FastAPI request object
        db: Database session

    Returns:
        Access token and user data

    Raises:
        HTTPException: If credentials are invalid or user is inactive
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Update last login
    user.last_login = datetime.utcnow()

    # Create session token
    token = generate_token()
    ip_address, user_agent = get_client_info(request)

    session = UserSession(
        user_id=user.id,
        token=token,
        device_info=user_agent,
        ip_address=ip_address,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(session)
    db.commit()
    db.refresh(user)

    logger.info(f"User signed in: {user.email}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.post("/signout")
async def signout(token: str, db: Session = Depends(get_db)):
    """
    Sign out user by invalidating session token.

    Args:
        token: Authentication token
        db: Database session

    Returns:
        Success message
    """
    session = db.query(UserSession).filter(UserSession.token == token).first()

    if session:
        session.is_active = False
        db.commit()
        logger.info(f"User signed out: user_id={session.user_id}")

    return {"message": "Signed out successfully"}


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get user data by ID.

    Args:
        user_id: User's unique identifier
        db: Database session

    Returns:
        User data

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.delete("/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Delete user account and all associated data.

    Args:
        user_id: User's unique identifier
        db: Database session

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    logger.info(f"User deleted: {user.email}")
    return None


@router.get("/verify-token")
async def verify_token(token: str, db: Session = Depends(get_db)):
    """
    Verify if authentication token is valid.

    Args:
        token: Authentication token
        db: Database session

    Returns:
        Token validity and user data

    Raises:
        HTTPException: If token is invalid or expired
    """
    session = db.query(UserSession).filter(
        UserSession.token == token,
        UserSession.is_active == True
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Check if token is expired
    if session.expires_at < datetime.utcnow():
        session.is_active = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )

    # Get user data
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return {
        "valid": True,
        "user": UserResponse.from_orm(user)
    }
