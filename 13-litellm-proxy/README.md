# 13 - LiteLLM (the LLM Proxy)

See the 4 features that make teams use an LLM proxy at scale:
caching, retries, rate limiting, and budget tracking.

```
Your app → LiteLLM → Groq/OpenAI/Anthropic/...
           (caching, retries, rate limits, cost tracking)
```

## What's in this folder
- `litellm_features.py` — runnable demo of all 4 features

## Setup

Already installed if you followed along. Otherwise:
```bash
uv pip install litellm --python ../.venv/bin/python3
```

## Run
```bash
cd 13-litellm-proxy
../.venv/bin/python3 litellm_features.py
```

Press Enter between each feature demo.

---

## The 4 features

### 1. Caching
Same question asked twice → the second is served from cache: instant and free.
```python
litellm.cache = Cache(type="local")
completion(model=MODEL, messages=msgs, caching=True)
```
In the demo you'll see ~60x speedup on the cached call, costing $0.

### 2. Retries on failure
LiteLLM auto-retries failed calls (network blips, provider errors).
```python
completion(model=MODEL, messages=msgs, num_retries=3)
```
Bonus — fallbacks: if the primary model fails, try a backup automatically.
```python
completion(model="groq/...", fallbacks=["groq/llama-3.1-8b-instant"])
```

### 3. Rate limiting
Cap how many requests go through per time window.
The demo uses a simple rate limiter (3 requests / 10 seconds) so you can SEE
requests get blocked. In production, the LiteLLM **proxy server** enforces this
per-user using Redis.

### 4. Budget tracking ($100 example)
Track the cost of each call, sum it up, and block when the budget is hit.
```python
call_cost = litellm.completion_cost(completion_response=resp)
spent += call_cost
if spent >= BUDGET_LIMIT:
    # block further requests
```
You'll see cost per call, running total, and remaining out of $100.

---

## Important notes (things I hit while building this)

**1. LiteLLM model format:** use `provider/model`. For Groq it's `groq/openai/gpt-oss-20b`.

**2. Cost calculation needs pricing data:** LiteLLM only auto-calculates cost for
models in its built-in pricing table. `gpt-oss-20b` isn't mapped, so
`completion_cost()` fails on it. The demo handles this by computing cost manually
from token counts (per-token prices defined in the code). For mapped models
(like OpenAI's), `completion_cost()` works out of the box.

**3. Library vs proxy server:** This demo uses LiteLLM as a Python **library**
(everything in one script). LiteLLM can also run as a standalone **proxy server**
that all your apps call — that's the true "dedicated LLM proxy" from the scaling
ladder. The proxy server enforces rate limits and budgets strictly using Redis.

To try the proxy server mode (advanced):
```bash
# Create a config.yaml, then:
litellm --config config.yaml
# Now call http://localhost:4000 like it's the OpenAI API
```

---

## Why this matters (recap)

At small scale, you call the LLM directly (like your other modules).
At large scale, all your servers route through ONE proxy so you can:
- Cache common answers (save money)
- Retry/fallback automatically (reliability)
- Cap the total request rate (don't exceed provider limits)
- Track and limit spend (budget control)

This is the "dedicated LLM proxy with rate limiting" line from the scaling ladder.


---

# Multi-User Gateway (real-world app)

`multi_user_gateway.py` — a production-style LLM gateway with **per-user credits and
rate limiting**, backed by Redis (shared state across all servers).

This answers: "How do I track how many credits each user used, how much is left,
block them when they cross it, and cap them to N requests per minute?"

## What it does
- **Credit tracking**: each user has a dollar budget. Every LLM call deducts its cost.
  When credits hit $0, further requests are blocked with HTTP 402.
- **Rate limiting**: each user can make max 5 requests per 60s. Exceeding it returns HTTP 429.
- **Per-user isolation**: alice's limits don't affect bob's — each has separate counters.
- **Usage dashboard**: see any user's usage, or all users at once.
- **Admin**: top up credits, set exact balance, reset everything.

## Why Redis
All the counters live in Redis, so limits are enforced **globally** across every server
and worker — not per-server. This is exactly how the LiteLLM proxy server does it internally.

Redis keys used (namespaced per user, in DB 2):
```
credits:<user>     STRING  → remaining dollars
spent:<user>       STRING  → total spent
ratelimit:<user>   STRING  → request count in current window (auto-expires after 60s)
```

## How rate limiting works (the classic Redis pattern)
```python
current = r.incr(key)              # atomically +1
if current == 1:
    r.expire(key, 60)              # first request sets the window
if current > 5:
    raise 429                      # over the limit
# when the key expires (60s), the count resets automatically
```

## Run
```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — the gateway
cd 13-litellm-proxy && ../.venv/bin/python3 multi_user_gateway.py

# Terminal 3 — the test
cd 13-litellm-proxy && ../.venv/bin/python3 test_multi_user.py
```

## What the test shows
```
[1] RATE LIMITING — alice sends 6 requests (limit 5/min):
    Request 1-5: OK
    Request 6: BLOCKED (429) — try again in 58s

[2] USER ISOLATION — bob asks: OK (separate limits from alice)

[3] CREDIT EXHAUSTION — charlie has a tiny budget:
    Request 1-2: OK
    Request 3: BLOCKED (402) — out of credits!

[4] USAGE DASHBOARD — all users' spend + remaining
```

## Try it in the browser
Open http://localhost:8000/docs and:
1. POST /ask — add header `X-User-Id: alice`, body `{"question": "..."}`
2. GET /usage/alice — see her credits/spend
3. GET /usage — see all users
4. POST /admin/topup/alice?amount=0.05 — give her more credits

## HTTP status codes used
- **402 Payment Required** — out of credits (standard for billing/quota)
- **429 Too Many Requests** — rate limit exceeded (standard for rate limiting)

## Notes / things to know
- Credits can dip slightly negative: we check BEFORE the call and deduct AFTER, so the
  call that crosses zero still completes, then the next one is blocked. To prevent any
  overage, you'd estimate cost upfront and reserve it before calling.
- In a real app, `X-User-Id` would come from an auth token / API key, not a raw header.
- For heavy traffic, use atomic Redis operations or Lua scripts to avoid race conditions
  (two simultaneous requests both passing the credit check). LiteLLM's proxy handles this.
