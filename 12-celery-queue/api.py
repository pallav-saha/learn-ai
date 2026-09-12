"""
FastAPI app — the web server that queues jobs instead of doing them directly.

The key idea:
    Old way: endpoint calls LLM → user waits 3-30s → returns answer
    Queue way: endpoint drops job in queue → responds INSTANTLY with a job_id
               → user checks back later for the result

Run:
    cd 12-celery-queue && ../.venv/bin/python3 api.py

You also need (in separate terminals):
    1. Redis:  redis-server
    2. Worker: cd 12-celery-queue && ../.venv/bin/celery -A tasks worker --loglevel=info --pool=threads
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from tasks import process_llm_request, slow_batch_job, celery_app

app = FastAPI(title="Celery Queue Demo")


class QuestionRequest(BaseModel):
    question: str


# ============================================================
# STEP 1: SUBMIT A JOB (responds instantly)
# ============================================================

@app.post("/ask")
async def ask(req: QuestionRequest):
    """
    Submit a question. Does NOT wait for the LLM.
    Drops the job in the queue and returns a job_id immediately.
    """
    # .delay() = "put this job in the queue, don't run it here"
    # Returns instantly — the worker will run it in the background
    job = process_llm_request.delay(req.question)

    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Your question is being processed. Check /result/{job_id}",
    }


@app.post("/batch")
async def batch(item_count: int = 5):
    """Submit a long batch job — returns instantly."""
    job = slow_batch_job.delay(item_count)
    return {"job_id": job.id, "status": "queued"}


# ============================================================
# STEP 2: CHECK THE RESULT (poll this until done)
# ============================================================

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    """
    Check the status/result of a job.

    Possible states:
      PENDING    = job is waiting in the queue (worker hasn't picked it up)
      PROCESSING = worker is running it right now
      SUCCESS    = done! result is available
      FAILURE    = something went wrong
    """
    # Look up the job by its ID in Redis
    result = AsyncResult(job_id, app=celery_app)

    if result.state == "PENDING":
        return {"job_id": job_id, "status": "PENDING", "message": "Waiting in queue..."}

    elif result.state == "PROCESSING":
        return {
            "job_id": job_id,
            "status": "PROCESSING",
            "info": result.info,  # the meta we set in update_state
        }

    elif result.state == "SUCCESS":
        return {
            "job_id": job_id,
            "status": "SUCCESS",
            "result": result.result,  # whatever the task returned
        }

    elif result.state == "FAILURE":
        return {
            "job_id": job_id,
            "status": "FAILURE",
            "error": str(result.info),
        }

    else:
        return {"job_id": job_id, "status": result.state}


# ============================================================
# QUEUE STATS
# ============================================================

@app.get("/")
async def home():
    return {
        "message": "Celery Queue Demo",
        "how_to_use": [
            "1. POST /ask with {'question': 'What is Python?'} → get a job_id",
            "2. GET /result/{job_id} → poll until status is SUCCESS",
            "3. See the answer in the result",
        ],
        "docs": "http://localhost:8000/docs",
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  Celery Queue Demo — API")
    print("=" * 55)
    print()
    print("  Make sure these are ALSO running:")
    print("    1. redis-server")
    print("    2. celery -A tasks worker --loglevel=info --pool=threads")
    print()
    print("  API:  http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8000)
