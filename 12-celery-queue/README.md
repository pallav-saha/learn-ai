# 12 - Celery Queue (LLM requests in the background)

See how a task queue works. Instead of making users wait for the LLM,
you drop jobs in a queue and workers process them in the background.

```
                                      ┌─ Worker 1 ─┐
POST /ask → FastAPI → Redis (queue) → ┤  Worker 2  │ → LLM
              │                       └─ Worker 3 ─┘
              └→ returns job_id INSTANTLY

GET /result/{job_id} → checks Redis → returns answer when ready
```

## What's in this folder
- `tasks.py` — defines the background work (the LLM call)
- `api.py` — FastAPI server that queues jobs and returns job_ids
- `test_queue.py` — submits 3 questions and polls for results

## The two roles of Redis here
- **Broker**: the queue that holds pending jobs
- **Backend**: stores results after jobs finish

---

## Setup (one time)

**1. Install Redis:**
```bash
brew install redis
```

**2. Install Celery + httpx:**
```bash
uv pip install celery redis httpx --python ../.venv/bin/python3
```

---

## Running the demo — needs 4 terminals

### Terminal 1 — Redis (the queue storage)
```bash
redis-server
```

### Terminal 2 — Celery worker (processes jobs)
```bash
cd 12-celery-queue
../.venv/bin/celery -A tasks worker --loglevel=info --pool=threads --concurrency=2
```
Watch this terminal — you'll see jobs being picked up and processed live.

**Why `--pool=threads` on macOS?**
Celery's default "prefork" pool forks processes, which crashes on macOS
(SIGSEGV) when libraries like the OpenAI HTTP client run in forked children.
The `threads` pool avoids this. On Linux servers, the default prefork works fine.

Want more workers? Change `--concurrency`:
```bash
../.venv/bin/celery -A tasks worker --loglevel=info --pool=threads --concurrency=3
```

### Terminal 3 — FastAPI (the web server)
```bash
cd 12-celery-queue
../.venv/bin/python3 api.py
```

### Terminal 4 — Run the test
```bash
cd 12-celery-queue
../.venv/bin/python3 test_queue.py
```

---

## What you'll see

The test submits 3 questions. Notice:
- All 3 submit **instantly** (web server doesn't wait for the LLM)
- Then you poll each job: PENDING → PROCESSING → SUCCESS
- The worker terminal (Terminal 2) shows the jobs being processed

```
  Submitting 3 questions (notice how FAST this is):
    Submitted: 'What is Python in one sentence?'
      → job_id: abc123 (status: queued)
    ...
  All 3 submitted in 0.02s          ← instant!

  Now polling for results...
  Job 1 (abc123...):
    ... PENDING (waiting)
    ... PROCESSING (waiting)
    ✓ SUCCESS (45 tokens)
      Python is a high-level programming language...
```

---

## Try it in the browser

1. Open http://localhost:8000/docs
2. POST /ask with `{"question": "What is Docker?"}` → copy the job_id
3. GET /result/{job_id} → run it a few times, watch status change to SUCCESS

---

## Experiments

**1. Watch the queue fill up** — set `--concurrency=1` (one worker), submit 5 jobs.
They process one at a time. This is how you respect LLM rate limits.

**2. Add more workers** — set `--concurrency=3`, submit 5 jobs.
Three process in parallel. Faster, but uses more rate limit.

**3. Kill the worker mid-job** — Ctrl+C the worker while a job runs.
Restart it — Celery can redeliver the job (depending on config).

---

## Key takeaways

- **The web server never waits for the LLM.** It queues and responds instantly.
- **Workers run separately** and pull jobs at their own pace.
- **This respects rate limits** — control how many jobs run at once with `--concurrency`.
- **Tradeoff**: user must poll for the result (submit → check back), unlike
  streaming where they see the answer live.
- **Use queues for**: batch jobs, long tasks, high traffic.
- **Don't use queues for**: interactive chat (use streaming instead).

## Celery vs Bull
- **Celery** = Python (this example)
- **Bull** = Node.js/JavaScript (same concept, different language)
- Both typically use Redis as the broker.
