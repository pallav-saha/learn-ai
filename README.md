# AI Fundamentals — Learning Journey

A hands-on project covering AI/ML engineering from scratch — starting with what an
LLM is, and building all the way up to production concerns (load balancing, queues,
evaluation, guardrails, and observability).

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
09-chat-with-docs/       ← Real deployable project (RAG + FastAPI combined)
10-streaming/            ← Token streaming, SSE vs WebSocket, token usage
11-nginx-loadbalancing/  ← Scaling out with nginx in front of app replicas
12-celery-queue/         ← Background jobs / task queues with Celery
13-litellm-proxy/        ← One gateway in front of many LLM providers
14-evaluation/           ← Judging output quality (LLM-as-judge, metrics)
15-guardrails/           ← Input/output safety, prompt injection, validation
16-structured-outputs/   ← JSON mode, Pydantic schemas, function calling
17-observability/        ← Tracing, spans, latency & token metrics, debugging runs
notes/                   ← Reference notes (async, full Q&A)
```

## Setup

```bash
make setup    # creates .venv and installs all dependencies
```

## Run any script

```bash
make run file=01-llm-basics/01_llm_basics.py
make run file=03-agents/01_agent_basics.py
make run file=05-rag/03_rag_chromadb.py
```

Or run directly with the project virtualenv:

```bash
cd 16-structured-outputs
../.venv/bin/python3 03_function_calling.py
```

## Run the full project (Chat with Docs)

```bash
cd 09-chat-with-docs
../.venv/bin/uvicorn main:app --reload --port 8000
# Visit http://localhost:8000
```

## Requirements

- Python 3.12+
- uv (package manager)
- Groq API key (free at console.groq.com) in `.env` as `GROQ_API_KEY`
