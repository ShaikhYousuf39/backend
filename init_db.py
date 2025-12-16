"""
Database initialization script
Run this to create all database tables
"""
from database import init_db, test_connection

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DATABASE INITIALIZATION")
    print("="*60 + "\n")

    # Test connection first
    print("Step 1: Testing database connection...")
    if not test_connection():
        print("\n[ERROR] Database connection failed!")
        print("Please check your DATABASE_URL in .env file")
        exit(1)

    print("[SUCCESS] Database connection established!")

    # Initialize database
    print("\nStep 2: Creating database tables...")
    try:
        init_db()
        print("\n[SUCCESS] Database initialized successfully!")

        print("\n" + "="*60)
        print("  DATABASE READY!")
        print("="*60)
        print("\nThe following tables have been created:")
        print("  - users")
        print("  - user_sessions")
        print("  - user_progress")
        print("  - bookmarks")
        print("  - chat_history")
        print("  - user_preferences")
        print("  - analytics")
        print("\n" + "="*60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Database initialization failed: {str(e)}")
        exit(1)
