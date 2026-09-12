# 05 - RAG (Retrieval Augmented Generation)

## What's in this folder
- `01_rag_basics.py` — RAG with keyword search (simplest version)
- `02_rag_basics_embedding.py` — RAG with real embeddings (semantic search)
- `03_rag_chromadb.py` — RAG with ChromaDB (persistent vector database)
- `04_rag_hybrid.py` — Hybrid: documents via ChromaDB + tables via pandas code
- `05_rag_pgvector.py` — RAG with PostgreSQL + pgvector (reference)
- `file_loaders.py` — Extract text from PDF, DOCX, CSV, images, audio

## Run
```bash
cd 05-rag && ../.venv/bin/python3 03_rag_chromadb.py
```

## Key Q&A

**What is RAG?**
Search your documents, paste what you found into the prompt, let the LLM answer. That's it.
- **Retrieval** — find relevant text
- **Augmented** — add it to the prompt
- **Generation** — LLM answers from that context

**What is chunking?**
Splitting documents into small pieces (~400 chars) so you only send relevant parts to the LLM.

**What are embeddings?**
Text → list of numbers (vector) that represents meaning. Similar texts → similar numbers → found by semantic search.

**Why embeddings > keywords?**
"vacation days" won't keyword-match "paid time off." But their embeddings are close because same meaning.

**What is ChromaDB?**
A vector database. Stores embeddings permanently. No re-embedding on restart.

**What happens if chunk exceeds model's max input (256 tokens)?**
Silently truncated. Text beyond the limit is ignored. Keep chunks under ~500 chars for all-MiniLM-L6-v2.

**Why does RAG struggle with Excel/tables?**
RAG searches by meaning — bad at exact lookups ("Alice's salary"). For tables, let LLM write pandas code instead.

**ChromaDB: lower distance = more relevant?**
Yes. distance = 1 - similarity. 0.0 = identical, 1.0 = unrelated.
