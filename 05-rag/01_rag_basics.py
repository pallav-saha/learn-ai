"""
RAG (Retrieval Augmented Generation) — Chat with your documents!

This script shows how to:
1. Load a document
2. Split it into chunks
3. Find relevant chunks for a question (using simple keyword matching)
4. Send those chunks + question to the LLM
5. Get an answer based on YOUR data, not the LLM's training

Run: python3 01_rag_basics.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
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
    for filename in os.listdir(folder_path):
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
    
    Why chunk? Because:
    - LLMs have token limits — can't send entire books
    - Smaller chunks = more precise retrieval
    - We only want to send RELEVANT parts, not everything
    """
    # Split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    # If a paragraph is too long, split it further
    chunks = []
    for para in paragraphs:
        if len(para) > chunk_size:
            # Split long paragraphs into sentences
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
# STEP 3: RETRIEVE — Find the most relevant chunks for a question
# ============================================================

def find_relevant_chunks(question: str, chunks: list[str], top_k: int = 3) -> list[str]:
    """
    Find the most relevant chunks for a given question.
    
    This is a SIMPLE version using keyword matching.
    In production, you'd use embeddings + vector database (we'll cover that next).
    
    How it works:
    - Score each chunk by how many question words appear in it
    - Return the top_k highest scoring chunks
    """
    question_words = set(question.lower().split())
    # Remove common words that don't help with relevance
    stop_words = {"what", "is", "the", "a", "an", "how", "do", "does", "can", "i", 
                  "my", "our", "we", "in", "on", "at", "to", "for", "of", "and", "or",
                  "about", "tell", "me", "please", "explain", "describe"}
    question_words -= stop_words
    
    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        # Count how many question keywords appear in this chunk
        score = sum(1 for word in question_words if word in chunk_lower)
        scored_chunks.append((score, chunk))
    
    # Sort by score (highest first) and return top_k
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    relevant = [chunk for score, chunk in scored_chunks[:top_k] if score > 0]
    
    return relevant if relevant else [chunks[0]]  # Fallback to first chunk


# ============================================================
# STEP 4: GENERATE — Send context + question to LLM
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
def ask_with_context(question: str, context_chunks: list[str]) -> str:
    """
    Send the relevant document chunks + user's question to the LLM.
    
    This is where the "Augmented Generation" happens:
    - The LLM gets CONTEXT (your documents) it never saw during training
    - It generates an answer BASED ON that context
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
                    "Always cite which part of the context your answer comes from."
                ),
            },
            {
                "role": "user",
                "content": f"Context from documents:\n\n{context}\n\n---\n\nQuestion: {question}",
            },
        ],
        temperature=0.3,  # Low temperature = more factual, less creative
    )
    return response.choices[0].message.content


# ============================================================
# THE RAG PIPELINE — All steps together
# ============================================================

def rag_query(question: str, chunks: list[str]) -> str:
    """
    The full RAG pipeline:
    1. Find relevant chunks (RETRIEVE)
    2. Send to LLM with context (GENERATE)
    """
    print(f"\n🔍 Finding relevant chunks for: \"{question}\"")
    relevant = find_relevant_chunks(question, chunks)
    
    print(f"   📎 Found {len(relevant)} relevant chunk(s):")
    for i, chunk in enumerate(relevant, 1):
        preview = chunk[:80] + "..." if len(chunk) > 80 else chunk
        print(f"      {i}. {preview}")
    
    print(f"\n🤖 Asking LLM with context...")
    answer = ask_with_context(question, relevant)
    
    return answer


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  📚 RAG DEMO — Chat with your documents!")
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
    
    # Show what we have
    print(f"\n✅ Ready! I have {len(all_chunks)} document chunks loaded.")
    print("\nTry asking:")
    print('  • "What is the refund policy?"')
    print('  • "How many vacation days do employees get?"')
    print('  • "What is the hiring process?"')
    print('  • "Can I work remotely on Mondays?"')
    print('  • "What is the password requirement?"')
    print('  • "What is the expense limit for meals?"')
    
    print("\n" + "-" * 60)
    print("Type 'quit' to exit.\n")
    
    while True:
        question = input("❓ Your question: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not question:
            continue
        
        answer = rag_query(question, all_chunks)
        print(f"\n💬 Answer:\n{answer}")
        print("\n" + "=" * 60)
