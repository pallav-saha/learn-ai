"""
RAG with ChromaDB — Persistent vector database (local, no setup needed)

ChromaDB is a dedicated vector database that:
- Stores embeddings permanently on disk
- No re-embedding on restart — data persists
- Handles embedding automatically (you just pass text)
- Searches by meaning instantly

First run: Loads docs → chunks → embeds → saves to ChromaDB
Next runs: Just searches (instant, no re-embedding)

Run: python3 03_rag_chromadb.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-20b"


# ============================================================
# STEP 1: Set up ChromaDB
# ============================================================

# Data saved here — persists between runs!
CHROMA_DB_PATH = "./chroma_db"

# Create a persistent ChromaDB client (saves to disk)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Embedding function — ChromaDB will use this automatically
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# A "collection" is like a table — stores your documents + vectors
collection = chroma_client.get_or_create_collection(
    name="company_docs",
    embedding_function=embedding_fn,
)


# ============================================================
# STEP 2: Load and chunk documents
# ============================================================

def load_documents(folder_path: str) -> dict[str, str]:
    """Read ALL supported file types. Returns {filename: content}."""
    from file_loaders import load_file

    documents = {}
    for filename in sorted(os.listdir(folder_path)):
        filepath = os.path.join(folder_path, filename)
        try:
            content = load_file(filepath)
            if content.strip():
                documents[filename] = content
                print(f"   📄 Loaded: {filename} ({len(content)} chars)")
        except (ValueError, ImportError) as e:
            print(f"   ⚠️  Skipped: {filename} — {e}")
        except Exception as e:
            print(f"   ❌ Error: {filename} — {e}")
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
# STEP 3: Add documents to ChromaDB (only new ones)
# ============================================================

def index_documents(folder_path: str):
    """
    Load, chunk, and store documents in ChromaDB.
    Smart: skips documents already in the database.
    """
    documents = load_documents(folder_path)
    if not documents:
        print("   ❌ No documents found!")
        return

    all_chunks = []
    for filename, content in documents.items():
        chunks = chunk_text(content, source=filename)
        all_chunks.extend(chunks)

    # Check what's already stored
    existing_count = collection.count()
    existing_ids = set()
    if existing_count > 0:
        existing = collection.get()
        existing_ids = set(existing["ids"])
        print(f"   📦 Database already has {existing_count} chunks.")

    # Only add new chunks
    new_texts = []
    new_ids = []
    new_metadatas = []

    for chunk in all_chunks:
        chunk_id = f"{chunk['source']}_{chunk['chunk_index']}"
        if chunk_id not in existing_ids:
            new_texts.append(chunk["text"])
            new_ids.append(chunk_id)
            new_metadatas.append({
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
            })

    if new_texts:
        # ChromaDB embeds AND stores in one call!
        collection.add(
            documents=new_texts,
            ids=new_ids,
            metadatas=new_metadatas,
        )
        print(f"   ✅ Added {len(new_texts)} new chunks.")
    else:
        print(f"   ✅ All documents already indexed.")

    print(f"   📊 Total chunks in database: {collection.count()}")


# ============================================================
# STEP 4: Search ChromaDB
# ============================================================

def search(question: str, top_k: int = 3) -> list[dict]:
    """
    Search ChromaDB — it handles everything:
    1. Embeds your question
    2. Compares to all stored vectors
    3. Returns closest matches
    """
    results = collection.query(
        query_texts=[question],
        n_results=top_k,
    )

    formatted = []
    for i in range(len(results["documents"][0])):
        formatted.append({
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "distance": results["distances"][0][i],
        })
    return formatted


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
                    "If the answer is not in the context, say 'I don't have that information in the documents.' "
                    "Cite the source file when possible. Be concise."
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
    """Full RAG: search DB → send to LLM → answer."""
    print(f"\n🔍 Searching database for: \"{question}\"")
    results = search(question)

    print(f"   📎 Found {len(results)} relevant chunks:")
    for i, r in enumerate(results, 1):
        preview = r['text'][:80] + "..." if len(r['text']) > 80 else r['text']
        print(f"      {i}. [dist: {r['distance']:.3f}] ({r['source']}) {preview}")

    print(f"\n🤖 Asking LLM...")
    answer = ask_with_context(question, results)
    return answer


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  📚 RAG WITH CHROMADB (Persistent Vector Database)")
    print("=" * 60)

    docs_folder = os.path.join(os.path.dirname(__file__), "..", "sample_docs")

    print("\n📂 Indexing documents...")
    index_documents(docs_folder)

    print(f"\n✅ Ready! Data persists at: {CHROMA_DB_PATH}/")
    print("   Next run will skip re-embedding — instant startup!")
    print("\n💡 Add more .txt files to sample_docs/ → re-run → only new ones indexed.")

    print("\nTry asking:")
    print('  • "What is the refund policy?"')
    print('  • "Can I work from home on Monday?"')
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
