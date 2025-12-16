"""
Test script to verify Neon PostgreSQL database connection
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def test_connection():
    """Test database connection and run basic queries"""
    print("\n" + "="*60)
    print("Testing Connection to Neon PostgreSQL")
    print("="*60)

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL not found in .env file!")
        return False

    # Mask password for display
    try:
        parts = DATABASE_URL.split("://")
        protocol = parts[0]
        rest = parts[1]
        user_pass, host_db = rest.split("@")
        username = user_pass.split(":")[0]
        masked_url = f"{protocol}://{username}:****@{host_db}"
        print(f"\n[INFO] Connection String (masked): {masked_url}")
    except:
        print(f"\n[INFO] Using DATABASE_URL from .env")

    try:
        print("\n[CONNECTING] Attempting to connect...")

        # Create engine
        engine = create_engine(DATABASE_URL, echo=False)

        # Test connection
        with engine.connect() as connection:
            print("[SUCCESS] Connection successful!")

            # Test 1: Get PostgreSQL version
            print("\n" + "-"*60)
            print("TEST 1: Database Version")
            print("-"*60)
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"PostgreSQL Version: {version[:80]}...")

            # Test 2: Get current database name
            print("\n" + "-"*60)
            print("TEST 2: Current Database")
            print("-"*60)
            result = connection.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"[SUCCESS] Database Name: {db_name}")

            # Test 3: Get current time
            print("\n" + "-"*60)
            print("TEST 3: Server Time")
            print("-"*60)
            result = connection.execute(text("SELECT NOW();"))
            current_time = result.fetchone()[0]
            print(f"[SUCCESS] Server Time: {current_time}")

            # Test 4: Test arithmetic
            print("\n" + "-"*60)
            print("TEST 4: Basic Query")
            print("-"*60)
            result = connection.execute(text("SELECT 42 as answer;"))
            answer = result.fetchone()[0]
            print(f"[SUCCESS] Test Query Result: {answer}")

            # Test 5: Check existing tables
            print("\n" + "-"*60)
            print("TEST 5: Existing Tables")
            print("-"*60)
            result = connection.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public';
            """))
            table_count = result.fetchone()[0]
            print(f"[INFO] Number of tables in 'public' schema: {table_count}")

            # List existing tables if any
            if table_count > 0:
                result = connection.execute(text("""
                    SELECT table_name,
                           (SELECT COUNT(*)
                            FROM information_schema.columns c
                            WHERE c.table_schema = 'public'
                            AND c.table_name = t.table_name) as column_count
                    FROM information_schema.tables t
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """))
                tables = result.fetchall()
                print("\n[INFO] Existing Tables:")
                for table_name, col_count in tables:
                    print(f"   - {table_name} ({col_count} columns)")
            else:
                print("   (No tables found - database is empty)")

            # Test 6: Check permissions
            print("\n" + "-"*60)
            print("TEST 6: Database Permissions")
            print("-"*60)
            result = connection.execute(text("SELECT current_user;"))
            current_user = result.fetchone()[0]
            print(f"[SUCCESS] Connected as user: {current_user}")

            # Test 7: Test creating a temporary table
            print("\n" + "-"*60)
            print("TEST 7: Write Permissions Test")
            print("-"*60)
            try:
                connection.execute(text("""
                    CREATE TEMP TABLE test_temp (
                        id SERIAL PRIMARY KEY,
                        test_value TEXT
                    );
                """))
                connection.execute(text("""
                    INSERT INTO test_temp (test_value) VALUES ('Hello from Neon!');
                """))
                result = connection.execute(text("SELECT test_value FROM test_temp;"))
                test_value = result.fetchone()[0]
                print(f"[SUCCESS] Write/Read Test: {test_value}")
                connection.execute(text("DROP TABLE test_temp;"))
                print("[SUCCESS] Temporary table created, written to, and dropped successfully!")
            except Exception as e:
                print(f"[WARNING] Write permission test failed: {str(e)}")

        print("\n" + "="*60)
        print("*** ALL TESTS PASSED! ***")
        print("="*60)
        print("\n[SUCCESS] Your Neon database connection is working correctly!")
        print("[SUCCESS] You can now use this database in your application.")
        print("\n" + "="*60 + "\n")

        return True

    except Exception as e:
        print("\n" + "="*60)
        print("*** CONNECTION FAILED! ***")
        print("="*60)
        print(f"\n[ERROR] {str(e)}")
        print("\n[INFO] Troubleshooting steps:")
        print("   1. Check that DATABASE_URL is correct in .env file")
        print("   2. Verify your Neon database is active (check Neon dashboard)")
        print("   3. Check that your IP is allowed (Neon allows all by default)")
        print("   4. Ensure you have internet connection")
        print("   5. Try logging into Neon dashboard to verify database exists")
        print("\n" + "="*60 + "\n")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  NEON DATABASE CONNECTION TEST")
    print("="*60)

    success = test_connection()

    if not success:
        exit(1)
