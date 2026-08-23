"""
RAG with Real Embeddings — Chat with your documents using semantic search!

This is the UPGRADED version of rag_basics.py.
Instead of keyword matching, it uses EMBEDDINGS (meaning-based search).

What's different:
- Uses a free local embedding model (all-MiniLM-L6-v2) — no API key needed
- Searches by MEANING, not just keywords
- "vacation days" will match "paid time off" because they mean the same thing

First run will download the embedding model (~90MB) — then it's cached forever.

Run: python3 rag_basics_embedding.py
"""

import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-20b"


# ============================================================
# STEP 1: LOAD — Read documents from a folder
# ============================================================

def load_documents(folder_path: str) -> list[str]:
    """Read all .txt files from a folder and return their content."""
    documents = []
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".txt"):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, "r") as f:
                content = f.read()
                documents.append(content)
                print(f"   📄 Loaded: {filename} ({len(content)} chars)")
    return documents


# ============================================================
# STEP 2: CHUNK — Split documents into smaller pieces
# ============================================================

def chunk_text(text: str, chunk_size: int = 200) -> list[str]:
    """
    Split text into chunks by paragraphs.
    Each chunk becomes one "searchable unit."
    """
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

    return chunks


# ============================================================
# STEP 3: EMBED — Convert text into number vectors
# ============================================================

print("\n🧠 Loading embedding model (first time downloads ~90MB)...")
# This model runs LOCALLY on your machine — free, no API key
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("   ✅ Embedding model ready!")


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Convert a list of texts into vectors (embeddings).

    Each text becomes a list of 384 numbers that represent its MEANING.
    Similar texts → similar numbers → close together in vector space.
    """
    vectors = embedding_model.encode(texts, show_progress_bar=False)
    return np.array(vectors)


# ============================================================
# STEP 4: RETRIEVE — Find most relevant chunks by meaning
# ============================================================

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Measure how similar two vectors are (0 = unrelated, 1 = identical meaning).

    This is the math behind "how close are two points in vector space?"
    """
    dot_product = np.dot(vec_a, vec_b)
    magnitude = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if magnitude == 0:
        return 0.0
    return dot_product / magnitude


def find_relevant_chunks(
    question: str,
    chunks: list[str],
    chunk_vectors: np.ndarray,
    top_k: int = 3,
) -> list[tuple[float, str]]:
    """
    Find the most relevant chunks using EMBEDDING similarity.

    1. Embed the question → get a vector
    2. Compare that vector to ALL chunk vectors
    3. Return the closest ones (highest similarity)

    This finds "paid time off" when you ask about "vacation days"
    because their vectors are close — even though the words differ!
    """
    # Embed the question
    question_vector = embedding_model.encode([question])[0]

    # Score each chunk by similarity to the question
    scores = []
    for i, chunk_vec in enumerate(chunk_vectors):
        similarity = cosine_similarity(question_vector, chunk_vec)
        scores.append((similarity, chunks[i]))

    # Sort by similarity (highest first)
    scores.sort(key=lambda x: x[0], reverse=True)

    # Return top_k results
    return scores[:top_k]


# ============================================================
# STEP 5: GENERATE — Send context + question to LLM
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
def ask_with_context(question: str, context_chunks: list[str]) -> str:
    """
    Send relevant document chunks + user's question to the LLM.
    The LLM answers based on YOUR data, not its training.
    """
    context = "\n\n---\n\n".join(context_chunks)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions based ONLY on the provided context. "
                    "If the answer is not in the context, say 'I don't have that information in the documents.' "
                    "Always cite which part of the context your answer comes from. Be concise."
                ),
            },
            {
                "role": "user",
                "content": f"Context from documents:\n\n{context}\n\n---\n\nQuestion: {question}",
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


# ============================================================
# THE RAG PIPELINE — All steps together
# ============================================================

def rag_query(question: str, chunks: list[str], chunk_vectors: np.ndarray) -> str:
    """
    The full RAG pipeline with embeddings:
    1. Embed the question
    2. Find most similar chunks (by meaning)
    3. Send to LLM with context
    """
    print(f"\n🔍 Searching by meaning for: \"{question}\"")
    results = find_relevant_chunks(question, chunks, chunk_vectors)

    print(f"   📎 Top {len(results)} relevant chunks (by similarity score):")
    context_chunks = []
    for i, (score, chunk) in enumerate(results, 1):
        preview = chunk[:80] + "..." if len(chunk) > 80 else chunk
        print(f"      {i}. [{score:.3f}] {preview}")
        context_chunks.append(chunk)

    print(f"\n🤖 Asking LLM with context...")
    answer = ask_with_context(question, context_chunks)

    return answer


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  📚 RAG WITH EMBEDDINGS — Semantic search!")
    print("=" * 60)

    # Step 1: Load documents
    print("\n📂 Loading documents...")
    docs_folder = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
    documents = load_documents(docs_folder)

    if not documents:
        print("❌ No documents found in sample_docs/ folder!")
        exit(1)

    # Step 2: Chunk all documents
    print("\n✂️  Chunking documents...")
    all_chunks = []
    for doc in documents:
        chunks = chunk_text(doc)
        all_chunks.extend(chunks)
    print(f"   Created {len(all_chunks)} chunks")

    # Step 3: Embed all chunks (this is the key difference!)
    print("\n🔢 Embedding chunks (converting text → vectors)...")
    chunk_vectors = embed_texts(all_chunks)
    print(f"   ✅ Created {len(chunk_vectors)} vectors, each with {chunk_vectors.shape[1]} dimensions")

    # Ready!
    print(f"\n✅ Ready! Semantic search is active.")
    print("\nTry asking (notice these use DIFFERENT words than the document):")
    print('  • "How many days off do I get?"         (doc says "vacation" & "paid time off")')
    print('  • "Can I get my money back?"            (doc says "refund")')
    print('  • "What are the rules for working from home?"  (doc says "remote work")')
    print('  • "How do I join the company?"          (doc says "hiring process")')
    print('  • "What are the password rules?"        (doc says "security policy")')

    print("\n" + "-" * 60)
    print("Type 'quit' to exit.\n")

    while True:
        question = input("❓ Your question: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not question:
            continue

        answer = rag_query(question, all_chunks, chunk_vectors)
        print(f"\n💬 Answer:\n{answer}")
        print("\n" + "=" * 60)
