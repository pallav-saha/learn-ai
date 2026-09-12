"""
RAG with PostgreSQL + pgvector — Vector search in a real database!

pgvector adds vector search to PostgreSQL, so you can store
documents, embeddings, AND your regular app data in one place.

SETUP (one-time):
1. Make sure PostgreSQL is running
2. Create the database and enable pgvector:
   
   psql postgres
   CREATE DATABASE ai_learning;
   \c ai_learning
   CREATE EXTENSION IF NOT EXISTS vector;
   \q

3. Update the DATABASE_URL in .env:
   DATABASE_URL=postgresql://pallabroy:yourpassword@localhost:5432/ai_learning

4. Run this script — it creates the table automatically.

Run: python3 05_rag_pgvector.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-20b"

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://pallabroy@localhost:5432/ai_learning"
)

# Embedding model (same as before)
print("🧠 Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
VECTOR_DIM = 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors


# ============================================================
# STEP 1: Set up PostgreSQL table with pgvector
# ============================================================

def setup_database():
    """
    Create the documents table with a vector column.
    
    This is regular SQL + one special column type: vector(384)
    That's all pgvector adds — a new column type for storing embeddings.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Enable pgvector extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create table — notice the 'embedding vector(384)' column
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            source VARCHAR(255),
            chunk_index INTEGER,
            embedding vector(384),
            UNIQUE(source, chunk_index)
        );
    """)

    # Create an index for fast vector search
    cur.execute("""
        CREATE INDEX IF NOT EXISTS documents_embedding_idx
        ON documents USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10);
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("   ✅ Database table ready!")


# ============================================================
# STEP 2: Load and chunk (same as before)
# ============================================================

def load_documents(folder_path: str) -> dict[str, str]:
    """Read all .txt files."""
    documents = {}
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".txt"):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, "r") as f:
                documents[filename] = f.read()
    return documents


def chunk_text(text: str, source: str, chunk_size: int = 300) -> list[dict]:
    """Split text into chunks with metadata."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    for para in paragraphs:
        if len(para) > chunk_size:
            sentences = para.split(". ")
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += ". " + sentence if current_chunk else sentence
            if current_chunk:
                chunks.append(current_chunk.strip())
        else:
            chunks.append(para)

    return [
        {"text": chunk, "source": source, "chunk_index": i}
        for i, chunk in enumerate(chunks)
    ]


# ============================================================
# STEP 3: Insert documents into PostgreSQL with embeddings
# ============================================================

def index_documents(folder_path: str):
    """
    Load docs, chunk them, embed them, and INSERT into PostgreSQL.
    Uses ON CONFLICT to skip duplicates (same as ChromaDB's smart indexing).
    """
    documents = load_documents(folder_path)
    if not documents:
        print("   ❌ No documents found!")
        return

    all_chunks = []
    for filename, content in documents.items():
        chunks = chunk_text(content, source=filename)
        all_chunks.extend(chunks)

    # Embed all chunk texts
    texts = [c["text"] for c in all_chunks]
    print(f"   🔢 Embedding {len(texts)} chunks...")
    vectors = embedding_model.encode(texts)

    # Insert into PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    inserted = 0
    for chunk, vector in zip(all_chunks, vectors):
        try:
            cur.execute(
                """
                INSERT INTO documents (text, source, chunk_index, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source, chunk_index) DO NOTHING
                """,
                (
                    chunk["text"],
                    chunk["source"],
                    chunk["chunk_index"],
                    vector.tolist(),  # Convert numpy array to Python list
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"   ⚠️ Error inserting chunk: {e}")

    conn.commit()

    # Get total count
    cur.execute("SELECT COUNT(*) FROM documents;")
    total = cur.fetchone()[0]

    cur.close()
    conn.close()

    if inserted > 0:
        print(f"   ✅ Inserted {inserted} new chunks.")
    else:
        print(f"   ✅ All documents already indexed.")
    print(f"   📊 Total chunks in database: {total}")


# ============================================================
# STEP 4: Search using pgvector (SQL!)
# ============================================================

def search(question: str, top_k: int = 3) -> list[dict]:
    """
    Search PostgreSQL using vector similarity.
    
    This is the key difference from ChromaDB:
    You write SQL! The '<=>' operator is pgvector's cosine distance.
    
    SELECT ... ORDER BY embedding <=> query_vector
    That's it — pgvector handles the rest.
    """
    # Embed the question
    question_vector = embedding_model.encode([question])[0].tolist()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Vector similarity search using SQL!
    cur.execute(
        """
        SELECT text, source, chunk_index, embedding <=> %s::vector AS distance
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (question_vector, question_vector, top_k),
    )

    results = []
    for row in cur.fetchall():
        results.append({
            "text": row[0],
            "source": row[1],
            "distance": row[3],
        })

    cur.close()
    conn.close()
    return results


# ============================================================
# STEP 5: RAG pipeline
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
def ask_with_context(question: str, context_chunks: list[dict]) -> str:
    """Send relevant chunks + question to LLM."""
    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in context_chunks
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions based ONLY on the provided context. "
                    "If the answer is not in the context, say 'I don't have that information.' "
                    "Cite the source file. Be concise."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {question}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def rag_query(question: str) -> str:
    """Full RAG: search PostgreSQL → send to LLM → answer."""
    print(f"\n🔍 Searching PostgreSQL for: \"{question}\"")
    results = search(question)

    print(f"   📎 Found {len(results)} relevant chunks:")
    for i, r in enumerate(results, 1):
        preview = r['text'][:80] + "..." if len(r['text']) > 80 else r['text']
        print(f"      {i}. [dist: {r['distance']:.4f}] ({r['source']}) {preview}")

    print(f"\n🤖 Asking LLM...")
    answer = ask_with_context(question, results)
    return answer


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  📚 RAG WITH POSTGRESQL + pgvector")
    print("=" * 60)

    # Setup database table
    print("\n🗄️  Setting up database...")
    try:
        setup_database()
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        print("\nSetup instructions:")
        print("  1. psql postgres")
        print("  2. CREATE DATABASE ai_learning;")
        print("  3. \\c ai_learning")
        print("  4. CREATE EXTENSION IF NOT EXISTS vector;")
        print("  5. \\q")
        print(f"\n  6. Add to .env: DATABASE_URL=postgresql://pallabroy@localhost:5432/ai_learning")
        exit(1)

    # Index documents
    docs_folder = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
    print("\n📂 Indexing documents...")
    index_documents(docs_folder)

    print(f"\n✅ Ready! Data stored in PostgreSQL (ai_learning database).")
    print("   You can query it with regular SQL too!")
    print("   Example: SELECT text, source FROM documents LIMIT 5;")

    print("\nTry asking:")
    print('  • "What is the refund policy?"')
    print('  • "Can I work from home?"')
    print('  • "How long is the hiring process?"')

    print("\n" + "-" * 60)
    print("Type 'quit' to exit.\n")

    while True:
        question = input("❓ Your question: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not question:
            continue

        answer = rag_query(question)
        print(f"\n💬 Answer:\n{answer}")
        print("\n" + "=" * 60)
