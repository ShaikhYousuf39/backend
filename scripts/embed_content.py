"""
Script to embed textbook content into Qdrant vector database.
Run this after creating or updating textbook content.
"""
import sys
import os
from pathlib import Path
import asyncio

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from services.embedding_service import EmbeddingService

# Load environment variables
load_dotenv()


async def embed_all_chapters():
    """Embed all chapters from the docs directory."""
    print(" Starting content embedding process...")

    # Initialize embedding service
    try:
        embedding_service = EmbeddingService()
        print("[OK] Connected to Qdrant")
    except Exception as e:
        print(f"[ERROR] Failed to initialize embedding service: {e}")
        print(" Make sure OPENAI_API_KEY and QDRANT_URL are set in .env")
        return

    # Find docs directory
    docs_paths = [
        Path("docs"),
        Path("../docs"),
        Path("../../docs"),
        Path("../physical-ai-textbook/docs"),
        Path("../../physical-ai-textbook/docs"),
    ]

    docs_path = None
    for path in docs_paths:
        if path.exists() and path.is_dir():
            docs_path = path
            break

    if not docs_path:
        print("[ERROR] Could not find docs directory")
        print(" Make sure you're running this from the backend directory")
        return

    print(f" Found docs directory: {docs_path.absolute()}")

    # Find all markdown files
    md_files = list(docs_path.rglob("*.md"))

    if not md_files:
        print("[ERROR] No markdown files found in docs directory")
        return

    print(f" Found {len(md_files)} markdown files")

    total_chunks = 0
    successful = 0
    failed = 0

    # Embed each file
    for md_file in md_files:
        try:
            # Read content
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Skip if file is too short
            if len(content) < 100:
                print(f"  Skipping {md_file.name} (too short)")
                continue

            # Generate chapter ID and title
            chapter_id = str(md_file.relative_to(docs_path)).replace('\\', '/')
            chapter_title = chapter_id.replace('.md', '').replace('/', ' - ').title()

            print(f"\n Processing: {chapter_title}")
            print(f"   File: {chapter_id}")

            # Embed content
            num_chunks = await embedding_service.embed_content(
                content=content,
                metadata={
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title
                }
            )

            total_chunks += num_chunks
            successful += 1
            print(f"   [OK] Embedded {num_chunks} chunks")

        except Exception as e:
            failed += 1
            print(f"   [ERROR] Failed to embed {md_file.name}: {e}")

    # Summary
    print("\n" + "="*60)
    print(" Embedding Summary:")
    print(f"   [OK] Successful files: {successful}")
    print(f"   [ERROR] Failed files: {failed}")
    print(f"    Total chunks created: {total_chunks}")
    print(f"    Stored in Qdrant collection: {embedding_service.collection_name}")
    print("="*60)

    if successful > 0:
        print("\n[SUCCESS] Content embedding complete! Your chatbot is ready to answer questions.")
    else:
        print("\n  No content was embedded. Please check the errors above.")


if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY not found in environment")
        print(" Please set it in your .env file")
        sys.exit(1)

    if not os.getenv("QDRANT_URL"):
        print("[ERROR] QDRANT_URL not found in environment")
        print(" Please set it in your .env file")
        sys.exit(1)

    # Run async function
    asyncio.run(embed_all_chapters())
