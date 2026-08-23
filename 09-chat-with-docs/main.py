"""
Chat with your Docs — A complete RAG web application

Upload files → Ask questions → Get answers from YOUR documents

Features:
- Upload PDF, DOCX, CSV, TXT files
- Automatic chunking + embedding + storage in ChromaDB
- Semantic search for relevant context
- LLM answers based on your documents only
- Conversation memory within a session
- Interactive API docs at /docs

Run: cd chat_with_docs && uvicorn main:app --reload --port 8000
Then visit: http://localhost:8000/docs
"""

import os
import shutil
import uuid
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI
import chromadb
from chromadb.utils import embedding_functions

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(
    title="Chat with your Docs",
    description="Upload documents and ask questions about them using AI",
    version="1.0.0",
)

# LLM client (async for FastAPI)
llm_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

# ChromaDB for document storage
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "vectordb")
os.makedirs(UPLOAD_DIR, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = chroma_client.get_or_create_collection(
    name="documents",
    embedding_function=embedding_fn,
)

# Conversation memory (per session, in-memory)
conversations: dict[str, list] = {}


# ============================================================
# FILE PROCESSING (load + chunk)
# ============================================================

def extract_text(filepath: str, filename: str) -> str:
    """Extract text from any supported file type."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        with open(filepath, "r") as f:
            return f.read()

    elif ext == ".pdf":
        import pdfplumber
        pages = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)

    elif ext in (".docx", ".doc"):
        from docx import Document
        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    elif ext in (".csv", ".xlsx", ".xls"):
        import pandas as pd
        if ext == ".csv":
            df = pd.read_csv(filepath)
            # Convert rows to text
            columns = df.columns.tolist()
            rows = []
            rows.append(f"Data with {len(df)} rows. Columns: {', '.join(columns)}")
            for _, row in df.iterrows():
                parts = [f"{col}: {row[col]}" for col in columns if pd.notna(row[col])]
                rows.append(", ".join(parts))
            return "\n".join(rows)
        else:
            # Excel: read ALL sheets
            all_sheets = pd.read_excel(filepath, sheet_name=None)  # None = all sheets
            all_text = []
            for sheet_name, df in all_sheets.items():
                columns = df.columns.tolist()
                rows = []
                rows.append(f"\nSheet: {sheet_name} ({len(df)} rows). Columns: {', '.join(columns)}")
                for _, row in df.iterrows():
                    parts = [f"{col}: {row[col]}" for col in columns if pd.notna(row[col])]
                    rows.append(", ".join(parts))
                all_text.append("\n".join(rows))
            return "\n\n".join(all_text)

    elif ext == ".json":
        import json as json_module
        with open(filepath, "r") as f:
            data = json_module.load(f)
        # Convert JSON to readable text
        return json_module.dumps(data, indent=2, default=str)

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = 400) -> list[str]:
    """Split text into chunks."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []

    for para in paragraphs:
        if len(para) > chunk_size:
            sentences = para.split(". ")
            current = ""
            for s in sentences:
                if len(current) + len(s) > chunk_size:
                    if current:
                        chunks.append(current.strip())
                    current = s
                else:
                    current += ". " + s if current else s
            if current:
                chunks.append(current.strip())
        else:
            chunks.append(para)

    return chunks


# ============================================================
# API MODELS
# ============================================================

class QuestionRequest(BaseModel):
    question: str
    session_id: str = "default"


class QuestionResponse(BaseModel):
    answer: str
    sources: list[str]
    chunks_used: int


class UploadResponse(BaseModel):
    filename: str
    chunks_created: int
    message: str


class StatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    uploaded_files: list[str]


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the chat UI."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path, "r") as f:
        return f.read()


@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document to be indexed.
    Supported: .pdf, .docx, .csv, .xlsx, .txt
    """
    # Validate file type
    ext = os.path.splitext(file.filename)[1].lower()
    supported = {".pdf", ".docx", ".doc", ".csv", ".xlsx", ".xls", ".txt", ".json"}
    if ext not in supported:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Supported: {supported}")

    # Save file to disk
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    try:
        text = extract_text(filepath, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from this file.")

    # Chunk the text
    chunks = chunk_text(text)

    # Delete old chunks from this file (in case of re-upload)
    existing = collection.get(where={"source": file.filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    # Store in ChromaDB
    ids = [f"{file.filename}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": file.filename, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas,
    )

    return UploadResponse(
        filename=file.filename,
        chunks_created=len(chunks),
        message=f"Successfully indexed {file.filename} ({len(chunks)} chunks, {len(text)} characters)",
    )


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(req: QuestionRequest):
    """
    Ask a question about your uploaded documents.
    Uses semantic search to find relevant context, then LLM answers.
    """
    if collection.count() == 0:
        raise HTTPException(status_code=400, detail="No documents uploaded yet. Upload files first using /upload")

    # Search for relevant chunks
    results = collection.query(
        query_texts=[req.question],
        n_results=min(3, collection.count()),
    )

    if not results["documents"][0]:
        raise HTTPException(status_code=404, detail="No relevant content found.")

    # Build context from top chunks (limit to ~3000 chars to stay under token limit)
    context_chunks = results["documents"][0]
    sources = list(set(m["source"] for m in results["metadatas"][0]))
    context = "\n\n---\n\n".join(context_chunks)
    # Trim context if too long (stay under ~4000 tokens)
    if len(context) > 6000:
        context = context[:6000] + "\n\n[...truncated for length]"

    # Get or create conversation history
    if req.session_id not in conversations:
        conversations[req.session_id] = []

    history = conversations[req.session_id]

    # Build messages for LLM
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant that answers questions based on the provided document context. "
                "If the answer is not in the context, say so. Cite which document your answer comes from. "
                "Be concise and accurate."
            ),
        },
    ]

    # Add conversation history (last 6 exchanges)
    messages.extend(history[-12:])

    # Add current question with context
    messages.append({
        "role": "user",
        "content": f"Document context:\n\n{context}\n\n---\n\nQuestion: {req.question}",
    })

    # Call LLM
    response = await llm_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
    )

    answer = response.choices[0].message.content

    # Save to conversation history
    history.append({"role": "user", "content": req.question})
    history.append({"role": "assistant", "content": answer})

    return QuestionResponse(
        answer=answer,
        sources=sources,
        chunks_used=len(context_chunks),
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get information about uploaded documents."""
    # Get unique files
    all_data = collection.get()
    files = set()
    if all_data["metadatas"]:
        files = set(m["source"] for m in all_data["metadatas"])

    return StatsResponse(
        total_documents=len(files),
        total_chunks=collection.count(),
        uploaded_files=sorted(files),
    )


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document and its chunks from the database."""
    existing = collection.get(where={"source": filename})
    if not existing["ids"]:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")

    collection.delete(ids=existing["ids"])

    # Remove file from uploads
    filepath = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    return {"message": f"Deleted {filename} ({len(existing['ids'])} chunks removed)"}


@app.delete("/reset")
async def reset_all():
    """Delete all documents and reset the database."""
    chroma_client.delete_collection("documents")
    # Recreate empty collection
    global collection
    collection = chroma_client.get_or_create_collection(
        name="documents",
        embedding_function=embedding_fn,
    )
    # Clear uploads
    for f in os.listdir(UPLOAD_DIR):
        os.remove(os.path.join(UPLOAD_DIR, f))
    # Clear conversations
    conversations.clear()

    return {"message": "All documents and conversations cleared."}


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Chat with your Docs")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
