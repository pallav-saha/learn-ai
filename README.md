# AI Fundamentals — Learning Journey

A hands-on project covering AI/ML fundamentals from scratch.

## Structure

```
01-llm-basics/           ← What LLMs are, prompt → completion
02-prompt-engineering/   ← 6 techniques to get better outputs
03-agents/               ← AI agents with tools (the agent loop)
04-fastapi/              ← Async APIs, Flask vs FastAPI
05-rag/                  ← RAG, embeddings, vector databases, file loaders
06-multi-agent/          ← Multi-agent patterns (parallel, debate, manager)
07-threading/            ← Threading vs multiprocessing, parallelism
08-memory/               ← Short-term, long-term, semantic memory
09-chat-with-docs/       ← Real deployable project (everything combined)
sample_docs/             ← Sample files for RAG demos
notes/                   ← Reference notes (async, full Q&A)
```

## Setup

```bash
make setup    # creates .venv and installs all dependencies
```

## Run any script

```bash
make run file=01-llm-basics/llm_basics.py
make run file=03-agents/agent_basics.py
make run file=05-rag/rag_chromadb.py
```

## Run the full project (Chat with Docs)

```bash
cd chat_with_docs
../.venv/bin/uvicorn main:app --reload --port 8000
# Visit http://localhost:8000
```

## Requirements

- Python 3.12+
- uv (package manager)
- Groq API key (free at console.groq.com) in `.env`
