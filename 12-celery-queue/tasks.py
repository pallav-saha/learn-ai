"""
Celery Tasks — the background work definitions.

This file defines WHAT work the workers do.
The workers (started separately) pull jobs from the queue and run these functions.

Architecture:
    FastAPI (api.py) → drops job in queue → Redis → Worker picks it up → runs task here

Redis plays two roles:
    1. Broker: the queue that holds pending jobs
    2. Backend: stores the results when jobs finish
"""

import os
import time
from celery import Celery
from dotenv import load_dotenv
from openai import OpenAI  # Note: SYNC client (Celery workers are sync by default)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============================================================
# CELERY SETUP
# ============================================================
# broker  = where jobs wait in line (Redis)
# backend = where results are stored after jobs finish (Redis)
celery_app = Celery(
    "llm_tasks",
    broker="redis://localhost:6379/0",   # the QUEUE
    backend="redis://localhost:6379/1",  # the RESULT store
)

# Optional config
celery_app.conf.update(
    task_track_started=True,       # mark jobs as "STARTED" when a worker picks them up
    task_time_limit=120,           # kill a task if it runs longer than 2 minutes
    worker_prefetch_multiplier=1,  # each worker takes ONE job at a time (fair distribution)
)

# LLM client (sync — Celery tasks are regular functions, not async)
llm_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# THE TASK — this runs on a WORKER, not in your web server
# ============================================================

@celery_app.task(bind=True)
def process_llm_request(self, question: str):
    """
    A background task that calls the LLM.

    @celery_app.task = "this function can be queued and run by a worker"
    bind=True         = gives access to 'self' so we can update progress

    When you call process_llm_request.delay("hello"):
        - The job goes into Redis (the queue)
        - A worker picks it up and runs THIS function
        - The return value is stored in Redis (the backend)
    """
    # Update state so the API can show progress
    self.update_state(state="PROCESSING", meta={"status": "Calling the LLM..."})

    print(f"  [Worker] Processing question: {question}")

    # Simulate this being slow / rate-limited work
    time.sleep(1)

    # Actually call the LLM
    response = llm_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": question},
        ],
        temperature=0.7,
    )

    answer = response.choices[0].message.content
    print(f"  [Worker] Done. Answer length: {len(answer)} chars")

    # Whatever we return gets stored as the job result
    return {
        "question": question,
        "answer": answer,
        "tokens_used": response.usage.total_tokens,
    }


@celery_app.task
def slow_batch_job(item_count: int):
    """
    A second example: a long batch job.
    Shows why queues are good for work that takes a long time.
    """
    print(f"  [Worker] Starting batch job for {item_count} items...")
    results = []
    for i in range(item_count):
        time.sleep(0.5)  # Simulate processing each item
        results.append(f"item_{i}_processed")
        print(f"  [Worker] Processed item {i + 1}/{item_count}")
    return {"processed": item_count, "results": results}
