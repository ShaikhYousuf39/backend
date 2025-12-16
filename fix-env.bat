@echo off
echo Fixing DATABASE_URL in .env file...
echo.
echo Current DATABASE_URL has invalid format.
echo.
echo It should be:
echo DATABASE_URL=postgresql://neondb_owner:npg_uU2HQ5AyZRqp@ep-proud-bonus-aeaxh84n-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require
echo.
echo OR for testing, just use SQLite:
echo DATABASE_URL=sqlite:///./test.db
echo.
echo Please edit your .env file manually:
notepad .env
