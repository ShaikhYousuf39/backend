"""
Database configuration and connection management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from models import Base

# Load environment variables
load_dotenv()

# Normalize database URL to use psycopg driver
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Force psycopg driver if user provided plain postgresql://
if DATABASE_URL.startswith("postgresql://") and "+psycopg://" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,           # Number of connections to maintain
    max_overflow=10,       # Max additional connections if pool is full
    pool_timeout=30,       # Timeout for getting connection from pool
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo=False             # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database - create all tables
    Call this when starting the application
    """
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def get_db() -> Session:
    """
    Dependency for FastAPI endpoints to get database session
    Usage in FastAPI:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def drop_all_tables():
    """
    WARNING: This will delete all data!
    Only use for development/testing
    """
    print("WARNING: Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped!")


def reset_database():
    """
    Reset database - drop all tables and recreate
    WARNING: This will delete all data!
    """
    drop_all_tables()
    init_db()
    print("Database reset complete!")


# Test database connection
def test_connection():
    """Test database connection"""
    try:
        engine.connect()
        print("Database connection successful!")
        return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False
