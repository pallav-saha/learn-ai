# 04 - FastAPI + Async/Await

## What's in this folder
- `app.py` — FastAPI API with 3 endpoints (/chat, /summarize, /code) using Groq LLM

## Run
```bash
cd 04-fastapi && ../.venv/bin/python3 -m uvicorn app:app --reload --port 8000
```
Visit: http://localhost:8000/docs

## Key Q&A

**Flask vs FastAPI?**
FastAPI is modern (2018+). Async, auto-validation with Pydantic, free interactive docs at `/docs`.

**What is async/await?**
`await` = "this goes over the network, don't freeze while waiting." The server handles other requests during the wait.

**When to use await:**
Ask: "Does this function leave my computer?" YES (API, DB, file I/O) → await. NO (math, sorting) → no await.

**What is `request.get_json()` / Pydantic models?**
FastAPI auto-validates request bodies. Define a class with fields → if request is missing a field, FastAPI returns an error automatically.

**What about CPU-heavy work in async?**
Use `asyncio.to_thread(heavy_function)` to avoid blocking other requests.

**Key insight:**
Async doesn't make code faster — it makes the server handle MORE users simultaneously by not wasting time waiting.
