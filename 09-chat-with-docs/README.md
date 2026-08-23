# Chat with your Docs

Upload documents and ask questions about them using AI.

## Quick Start

```bash
# From the project root:
cd chat_with_docs
../.venv/bin/uvicorn main:app --reload --port 8000
```

Then visit: http://localhost:8000/docs (interactive API docs)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page with instructions |
| POST | `/upload` | Upload a file (PDF, DOCX, CSV, TXT) |
| POST | `/ask` | Ask a question about your documents |
| GET | `/stats` | See uploaded documents info |
| DELETE | `/documents/{filename}` | Remove a specific document |
| DELETE | `/reset` | Clear everything |

## Usage Examples

```bash
# Upload a file
curl -X POST http://localhost:8000/upload -F "file=@../sample_docs/company_policy.txt"

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}'

# Check what's uploaded
curl http://localhost:8000/stats

# Delete a file
curl -X DELETE http://localhost:8000/documents/company_policy.txt

# Reset everything
curl -X DELETE http://localhost:8000/reset
```

## What it uses (everything you learned!)

- **FastAPI** — async web framework
- **ChromaDB** — vector database for embeddings
- **Sentence Transformers** — local embedding model
- **Groq LLM** — generates answers
- **File loaders** — PDF, DOCX, CSV, TXT support
- **Chunking** — splits documents for better search
- **Conversation memory** — remembers within a session
