"""
Main FastAPI application for Physical AI Textbook backend.
Production-ready with database integration.
"""
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routes
from routes import auth, chat, content, progress
from database import init_db, test_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Physical AI Textbook API...")

    # Test database connection
    try:
        if test_connection():
            logger.info("Database connection successful!")
        else:
            logger.error("Database connection failed!")
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")

    # Initialize database tables
    try:
        init_db()
        logger.info("Database tables initialized!")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        logger.warning("API will start, but database features may not work!")

    # Verify required environment variables
    required_vars = ["OPENAI_API_KEY", "QDRANT_URL", "DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Some features may not work correctly!")
    else:
        logger.info("All required environment variables are set")

    logger.info("API startup complete!")

    yield

    # Shutdown
    logger.info("Shutting down Physical AI Textbook API...")


# Create FastAPI app
app = FastAPI(
    title="Physical AI & Humanoid Robotics Textbook API",
    description="Production-ready AI-native textbook backend with RAG chatbot, authentication, and progress tracking",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

logger.info(f"CORS enabled for origins: {cors_origins}")


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat & RAG"])
app.include_router(content.router, prefix="/api/content", tags=["Content & Personalization"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress & Analytics"])


# Root endpoint
@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "Physical AI & Humanoid Robotics Textbook API",
        "version": "2.0.0",
        "status": "running",
        "documentation": "/docs",
        "features": [
            "User authentication with session management",
            "RAG-powered Q&A chatbot (GPT-4o-mini + Qdrant)",
            "Text selection-based queries",
            "Content personalization (simplified/standard/advanced)",
            "Urdu translation with caching",
            "Progress tracking and analytics",
            "Bookmarks and notes",
            "User preferences management"
        ]
    }


# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for monitoring and deployments.
    """
    # Check database connection
    db_status = "healthy" if test_connection() else "unhealthy"

    return {
        "status": "healthy",
        "message": "API is running normally",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "healthy",
            "database": db_status,
            "qdrant": "healthy" if os.getenv("QDRANT_URL") else "not configured",
            "openai": "healthy" if os.getenv("OPENAI_API_KEY") else "not configured"
        }
    }


# API info endpoint
@app.get("/api/info")
async def api_info():
    """
    Get API configuration and status information.
    """
    return {
        "api_version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "features_enabled": {
            "authentication": True,
            "rag_chat": bool(os.getenv("OPENAI_API_KEY")),
            "vector_search": bool(os.getenv("QDRANT_URL")),
            "translation": bool(os.getenv("OPENAI_API_KEY")),
            "personalization": bool(os.getenv("OPENAI_API_KEY")),
            "progress_tracking": bool(os.getenv("DATABASE_URL")),
            "analytics": bool(os.getenv("DATABASE_URL"))
        },
        "cors_origins": cors_origins,
        "database": {
            "connected": test_connection(),
            "type": "PostgreSQL (Neon)"
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return {
        "error": "Not Found",
        "message": "The requested resource was not found",
        "path": str(request.url)
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(exc)}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later."
    }


if __name__ == "__main__":
    import uvicorn

    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("ENVIRONMENT", "development") == "development"

    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
