"""
Test script — submits jobs and polls for results.

Shows the full queue lifecycle:
    1. Submit a question → get job_id instantly
    2. Poll /result/{job_id} → PENDING → PROCESSING → SUCCESS
    3. See the answer

Run (after Redis, worker, and API are all running):
    ../.venv/bin/python3 test_queue.py
"""

import time
import httpx

API = "http://localhost:8000"


def main():
    print("=" * 55)
    print("  Testing the Celery Queue")
    print("=" * 55)
    print()

    with httpx.Client() as client:
        # --- Step 1: Submit 3 questions (all return instantly) ---
        print("  Submitting 3 questions (notice how FAST this is):\n")

        job_ids = []
        questions = [
            "What is Python in one sentence?",
            "What is FastAPI in one sentence?",
            "What is Redis in one sentence?",
        ]

        start = time.time()
        for q in questions:
            resp = client.post(f"{API}/ask", json={"question": q})
            job = resp.json()
            job_ids.append(job["job_id"])
            print(f"    Submitted: '{q}'")
            print(f"      → job_id: {job['job_id']} (status: {job['status']})")

        print(f"\n  All 3 submitted in {time.time() - start:.2f}s")
        print("  (The web server responded instantly — no LLM wait!)\n")

        # --- Step 2: Poll for results ---
        print("  Now polling for results...\n")

        for i, job_id in enumerate(job_ids):
            print(f"  Job {i + 1} ({job_id[:8]}...):")

            while True:
                resp = client.get(f"{API}/result/{job_id}")
                data = resp.json()
                status = data["status"]

                if status == "SUCCESS":
                    answer = data["result"]["answer"]
                    tokens = data["result"]["tokens_used"]
                    print(f"    ✓ SUCCESS ({tokens} tokens)")
                    print(f"      {answer}\n")
                    break
                elif status == "FAILURE":
                    print(f"    ✗ FAILED: {data.get('error')}\n")
                    break
                else:
                    print(f"    ... {status} (waiting)")
                    time.sleep(1)

    print("  Done! Each job was processed by a worker in the background.")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("\n  ERROR: Can't reach the API.")
        print("  Make sure ALL of these are running:")
        print("    1. redis-server")
        print("    2. celery -A tasks worker --loglevel=info --pool=threads")
        print("    3. python3 api.py")
