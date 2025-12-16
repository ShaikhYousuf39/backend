"""
Script to embed textbook content into Qdrant vector database.
This script reads all markdown files from the docs folder and creates embeddings.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import re

# Load environment variables
load_dotenv()

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

# Initialize Qdrant client
if qdrant_api_key:
    qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
else:
    qdrant_client = QdrantClient(url=qdrant_url)

COLLECTION_NAME = "physical_ai_textbook"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

def clean_text(text: str) -> str:
    """Remove non-ASCII characters for better compatibility."""
    # Remove emojis and special characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < text_length:
            # Look for sentence endings
            sentence_end = text.rfind('. ', start, end)
            if sentence_end != -1 and sentence_end > start + chunk_size // 2:
                end = sentence_end + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < text_length else text_length

    return chunks

def get_embedding(text: str) -> list[float]:
    """Get embedding vector from OpenAI."""
    try:
        response = openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {str(e)}")
        raise

def create_collection():
    """Create or recreate the Qdrant collection."""
    try:
        # Delete existing collection if it exists
        try:
            qdrant_client.delete_collection(collection_name=COLLECTION_NAME)
            print(f"Deleted existing collection: {COLLECTION_NAME}")
        except Exception:
            pass

        # Create new collection
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE
            )
        )
        print(f"Created new collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"Error creating collection: {str(e)}")
        raise

def process_markdown_file(file_path: Path) -> list[dict]:
    """
    Process a markdown file and return chunks with metadata.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of dictionaries containing text chunks and metadata
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Clean the content
        content = clean_text(content)

        # Extract title (first heading)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path.stem

        # Get relative path for better organization
        relative_path = str(file_path.relative_to(file_path.parents[2]))

        # Chunk the content
        chunks = chunk_text(content)

        # Create chunk objects with metadata
        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_objects.append({
                'text': chunk,
                'metadata': {
                    'title': title,
                    'file_path': relative_path,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            })

        return chunk_objects

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return []

def embed_documents():
    """Main function to embed all documents."""
    print("Starting content embedding process...")
    print(f"OpenAI API Key: {'Set' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print(f"Qdrant URL: {qdrant_url}")
    print(f"Qdrant API Key: {'Set' if qdrant_api_key else 'NOT SET'}")
    print()

    # Create collection
    create_collection()
    print()

    # Find all markdown files in docs folder
    docs_path = Path(__file__).parent.parent / "physical-ai-textbook" / "docs"

    if not docs_path.exists():
        print(f"Error: Docs folder not found at {docs_path}")
        sys.exit(1)

    markdown_files = list(docs_path.rglob("*.md"))

    if not markdown_files:
        print(f"Error: No markdown files found in {docs_path}")
        sys.exit(1)

    print(f"Found {len(markdown_files)} markdown files")
    print()

    # Process all files
    all_chunks = []
    for file_path in markdown_files:
        print(f"Processing: {file_path.relative_to(docs_path.parent.parent)}")
        chunks = process_markdown_file(file_path)
        all_chunks.extend(chunks)

    print()
    print(f"Total chunks to embed: {len(all_chunks)}")
    print()

    # Create embeddings and upload to Qdrant
    points = []
    for i, chunk_obj in enumerate(all_chunks):
        try:
            # Get embedding
            embedding = get_embedding(chunk_obj['text'])

            # Create point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    'text': chunk_obj['text'],
                    'title': chunk_obj['metadata']['title'],
                    'file_path': chunk_obj['metadata']['file_path'],
                    'chunk_index': chunk_obj['metadata']['chunk_index'],
                    'total_chunks': chunk_obj['metadata']['total_chunks']
                }
            )
            points.append(point)

            # Upload in batches of 100
            if len(points) >= 100 or i == len(all_chunks) - 1:
                qdrant_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points
                )
                print(f"Uploaded {i + 1}/{len(all_chunks)} chunks")
                points = []

        except Exception as e:
            print(f"Error embedding chunk {i}: {str(e)}")
            continue

    print()
    print("=" * 60)
    print(f"SUCCESS! Embedded {len(all_chunks)} chunks from {len(markdown_files)} files")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Vector dimension: {EMBEDDING_DIMENSION}")
    print(f"Distance metric: COSINE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        embed_documents()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)
