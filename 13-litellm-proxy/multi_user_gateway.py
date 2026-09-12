"""
Multi-User LLM Gateway — credits + rate limiting with Redis (real-world app)

This is what a production LLM app does to control usage per user:
  1. CREDIT TRACKING  — each user has a budget; every call deducts cost. Block at $0.
  2. RATE LIMITING    — each user can make max N requests per minute.
  3. USAGE DASHBOARD  — see how much each user has used and has left.

Why Redis? It's SHARED across all your servers/workers, so limits are enforced
globally (not per-server). This is exactly how the LiteLLM proxy server works internally.
Redis is fast but temporary (in-memory). Great for rate limits and caching, but for anything you can't afford to lose (like money/credits), you need a durable database as the source of truth, with Redis as a fast layer in front.
What a real production system does — Redis + a database together:

The right architecture for millions of users:
Don't store everything in Redis. Split by what needs speed vs. what needs permanence:
Key insight: Redis only holds ACTIVE users, not all of them.

Out of a million registered users, maybe only 10,000 are active at any moment. So:

Redis caches only those ~10,000 active users → tiny RAM footprint
The other 990,000 inactive users live only in the database (cheap disk)
When an inactive user shows up, load their data from DB into Redis (cache), use it, let it expire when they go idle

User makes a request:
  1. Check Redis for their credits
     - Found (active user)? → use it (fast)
     - Not found (was idle)? → load from database → put in Redis → use it
  2. Deduct cost in Redis (fast)
  3. Periodically (or on logout) → write the balance back to the database (permanent)
  4. Redis key expires after inactivity → frees the RAM
  
This is called cache-aside (or lazy loading). Redis stays small because idle users' data drops out automatically.

Run:
    # 1. Start Redis (separate terminal):
    redis-server

    # 2. Start this API:
    cd 13-litellm-proxy && ../.venv/bin/python3 multi_user_gateway.py

    # 3. Test it (separate terminal):
    cd 13-litellm-proxy && ../.venv/bin/python3 test_multi_user.py

Then open http://localhost:8000/docs to try it interactively.
"""

import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import redis
from litellm import completion

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

MODEL = "groq/openai/gpt-oss-20b"

# ============================================================
# REDIS — shared state across all servers
# ============================================================
# We use DB 2 here to avoid clashing with the Celery demo (DB 0/1).
r = redis.Redis(host="localhost", port=6379, db=2, decode_responses=True)

# ============================================================
# CONFIG
# ============================================================
DEFAULT_CREDITS = 0.01          # each new user starts with $0.01 of credits (tiny so you can hit the limit)
RATE_LIMIT_MAX = 5              # max requests...
RATE_LIMIT_WINDOW = 60          # ...per 60 seconds

# Groq gpt-oss-20b approximate pricing (LiteLLM doesn't have it mapped)
PRICE_INPUT = 0.10 / 1_000_000    # $ per input token
PRICE_OUTPUT = 0.50 / 1_000_000   # $ per output token


app = FastAPI(title="Multi-User LLM Gateway")


# ============================================================
# REDIS KEY HELPERS
# ============================================================
# We namespace keys by user so each user has their own counters.
#   credits:<user>         -> STRING, remaining dollars (float)
#   spent:<user>           -> STRING, total dollars spent (float)
#   ratelimit:<user>       -> STRING with TTL, count of requests in current window

def credits_key(user):   return f"credits:{user}"
def spent_key(user):     return f"spent:{user}"
def ratelimit_key(user): return f"ratelimit:{user}"


def ensure_user(user: str):
    """Give a new user their starting credits (only if they don't exist yet)."""
    if not r.exists(credits_key(user)):
        r.set(credits_key(user), DEFAULT_CREDITS)
        r.set(spent_key(user), 0.0)


# ============================================================
# RATE LIMITING (per user, sliding-ish window using Redis TTL)
# ============================================================

def check_rate_limit(user: str):
    """
    Allow max RATE_LIMIT_MAX requests per RATE_LIMIT_WINDOW seconds per user.

    How it works (the classic Redis rate-limit pattern):
      - Increment a counter key for this user.
      - On the FIRST request, set the key to expire after the window.
      - If the counter exceeds the max, block.
      - When the key expires, the count resets automatically.
    """
    key = ratelimit_key(user)
    current = r.incr(key)  # atomically +1 (creates key at 1 if new)

    if current == 1:
        # First request in this window — set the window to expire
        r.expire(key, RATE_LIMIT_WINDOW)

    if current > RATE_LIMIT_MAX:
        # Over the limit — find out how long until reset
        ttl = r.ttl(key)
        raise HTTPException(
            status_code=429,  # 429 = Too Many Requests
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX} requests per "
                   f"{RATE_LIMIT_WINDOW}s. Try again in {ttl}s.",
        )


# ============================================================
# CREDIT CHECK & DEDUCTION
# ============================================================

def check_credits(user: str):
    """Block the request if the user is out of credits."""
    remaining = float(r.get(credits_key(user)) or 0)
    if remaining <= 0:
        raise HTTPException(
            status_code=402,  # 402 = Payment Required
            detail=f"Out of credits. You've used your full budget. Remaining: ${remaining:.6f}",
        )


def calc_cost(response) -> float:
    """Compute the dollar cost of a call from token counts."""
    usage = response.usage
    return usage.prompt_tokens * PRICE_INPUT + usage.completion_tokens * PRICE_OUTPUT


def deduct_credits(user: str, cost: float):
    """Subtract cost from remaining, add to spent. Atomic via Redis."""
    # incrbyfloat with a negative number = subtract
    r.incrbyfloat(credits_key(user), -cost)
    r.incrbyfloat(spent_key(user), cost)


# ============================================================
# API MODELS
# ============================================================

class AskRequest(BaseModel):
    question: str


# ============================================================
# THE MAIN ENDPOINT — the whole gateway flow
# ============================================================

@app.post("/ask")
async def ask(req: AskRequest, x_user_id: str = Header(...)):
    """
    Ask the LLM a question.

    The user is identified by the 'X-User-Id' header (in a real app this would
    come from an auth token / API key). Each user has separate credits + rate limits.

    Flow (the order matters):
      1. Ensure the user exists (give starting credits)
      2. Check rate limit  → block with 429 if too many requests
      3. Check credits     → block with 402 if out of budget
      4. Call the LLM
      5. Deduct the cost from their credits
      6. Return the answer + their usage
    """
    user = x_user_id

    # 1. Make sure the user has a credit balance
    ensure_user(user)

    # 2. Rate limit check (raises 429 if exceeded)
    check_rate_limit(user)

    # 3. Credit check (raises 402 if broke)
    check_credits(user)

    # 4. Call the LLM
    response = completion(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": req.question},
        ],
        temperature=0.7,
    )
    answer = response.choices[0].message.content

    # 5. Deduct cost
    cost = calc_cost(response)
    deduct_credits(user, cost)

    # 6. Return answer + live usage snapshot
    remaining = float(r.get(credits_key(user)))
    spent = float(r.get(spent_key(user)))

    return {
        "user": user,
        "answer": answer,
        "cost_this_call": round(cost, 8),
        "credits_remaining": round(remaining, 8),
        "total_spent": round(spent, 8),
        "tokens": response.usage.total_tokens,
    }


# ============================================================
# USAGE DASHBOARD — see any user's usage
# ============================================================

@app.get("/usage/{user}")
async def get_usage(user: str):
    """See how much a single user has used and has left."""
    if not r.exists(credits_key(user)):
        raise HTTPException(status_code=404, detail=f"No such user: {user}")

    remaining = float(r.get(credits_key(user)))
    spent = float(r.get(spent_key(user)))
    rl_count = int(r.get(ratelimit_key(user)) or 0)
    rl_ttl = r.ttl(ratelimit_key(user))

    return {
        "user": user,
        "credits_remaining": round(remaining, 8),
        "total_spent": round(spent, 8),
        "starting_credits": DEFAULT_CREDITS,
        "requests_this_window": rl_count,
        "rate_limit": f"{RATE_LIMIT_MAX} per {RATE_LIMIT_WINDOW}s",
        "window_resets_in_seconds": rl_ttl if rl_ttl > 0 else 0,
    }


@app.get("/usage")
async def all_usage():
    """Admin view — see ALL users' usage at once."""
    users = []
    # Scan all credit keys to find every user
    for key in r.scan_iter(match="credits:*"):
        user = key.split(":", 1)[1]
        remaining = float(r.get(credits_key(user)))
        spent = float(r.get(spent_key(user)))
        users.append({
            "user": user,
            "credits_remaining": round(remaining, 8),
            "total_spent": round(spent, 8),
        })
    users.sort(key=lambda u: u["user"])
    return {"total_users": len(users), "users": users}


# ============================================================
# ADMIN — top up credits, reset everything
# ============================================================

@app.post("/admin/topup/{user}")
async def topup(user: str, amount: float = 0.01):
    """Add credits to a user (like buying more)."""
    ensure_user(user)
    r.incrbyfloat(credits_key(user), amount)
    remaining = float(r.get(credits_key(user)))
    return {"user": user, "added": amount, "credits_remaining": round(remaining, 8)}


@app.post("/admin/set/{user}")
async def set_credits(user: str, amount: float):
    """Set a user's remaining credits to an exact amount (for testing)."""
    ensure_user(user)
    r.set(credits_key(user), amount)
    return {"user": user, "credits_remaining": amount}


@app.delete("/admin/reset")
async def reset_all():
    """Wipe all users (clears the DB 2 we use)."""
    r.flushdb()
    return {"message": "All user data cleared."}


# ============================================================
# RUN
# ============================================================

@app.get("/")
async def home():
    return {
        "message": "Multi-User LLM Gateway",
        "config": {
            "starting_credits": DEFAULT_CREDITS,
            "rate_limit": f"{RATE_LIMIT_MAX} requests per {RATE_LIMIT_WINDOW}s per user",
        },
        "how_to_use": [
            "POST /ask with header 'X-User-Id: alice' and body {'question': '...'}",
            "GET /usage/alice → see one user's usage",
            "GET /usage → see all users",
            "POST /admin/topup/alice?amount=0.05 → add credits",
        ],
        "docs": "http://localhost:8000/docs",
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 55)
    print("  Multi-User LLM Gateway")
    print("=" * 55)
    print(f"  Starting credits/user: ${DEFAULT_CREDITS}")
    print(f"  Rate limit: {RATE_LIMIT_MAX} requests / {RATE_LIMIT_WINDOW}s per user")
    print()
    print("  Make sure redis-server is running!")
    print("  API:  http://localhost:8000")
    print("  Docs: http://localhost:8000/docs")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8000)
