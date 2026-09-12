"""
LiteLLM Features Demo — the LLM proxy in action.

Shows the 4 things a production LLM proxy gives you:
  1. CACHING       — repeat questions return instantly, for free
  2. RETRIES       — automatic retry on failure
  3. RATE LIMITING — cap requests per minute
  4. BUDGET        — track $ spent, block when limit hit ($100 example)

LiteLLM works as a Python library (this file) OR as a standalone proxy server.
Here we use it as a library so you can see everything in one script.

Run:
    cd 13-litellm-proxy && ../.venv/bin/python3 litellm_features.py
"""

import os
import time
from dotenv import load_dotenv

import litellm
from litellm import completion
from litellm.caching.caching import Cache

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============================================================
# CONFIG — point LiteLLM at Groq
# ============================================================
# LiteLLM uses "provider/model" format. For Groq: "groq/<model>"
MODEL = "groq/openai/gpt-oss-20b"

# Groq needs its key in this env var (LiteLLM reads it automatically)
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")

# Show LiteLLM's internal logs? Set True to see retries etc. in detail.
litellm.set_verbose = False


# ============================================================
# 1. CACHING — repeat questions cost nothing
# ============================================================

def demo_caching():
    print("=" * 60)
    print("  1. CACHING")
    print("=" * 60)
    print()
    print("  Enable in-memory caching. Same question twice = second is FREE + instant.\n")

    # Turn on caching (in-memory; can also use Redis/disk)
    litellm.cache = Cache(type="local")

    question = "What is the capital of France? Answer in one word."
    messages = [{"role": "user", "content": question}]

    # --- First call: hits the LLM ---
    print("  First call (hits the LLM):")
    start = time.time()
    resp1 = completion(model=MODEL, messages=messages, caching=True)
    elapsed1 = time.time() - start
    print(f"    Answer: {resp1.choices[0].message.content.strip()}")
    print(f"    Time: {elapsed1:.2f}s")
    print(f"    Tokens used: {resp1.usage.total_tokens}")

    # --- Second call: SAME question, served from cache ---
    print("\n  Second call (SAME question — from cache):")
    start = time.time()
    resp2 = completion(model=MODEL, messages=messages, caching=True)
    elapsed2 = time.time() - start
    print(f"    Answer: {resp2.choices[0].message.content.strip()}")
    print(f"    Time: {elapsed2:.4f}s  ← way faster!")
    print(f"    Cache hit: {'YES' if elapsed2 < elapsed1 / 2 else 'no'}")

    print(f"\n  Speedup: {elapsed1 / max(elapsed2, 0.0001):.0f}x faster, and the 2nd call cost $0.")
    print("  Real apps cache common questions to save money + latency.\n")

    # Turn caching off for the other demos
    litellm.cache = None


# ============================================================
# 2. RETRIES — automatic retry on failure
# ============================================================

def demo_retries():
    print("=" * 60)
    print("  2. RETRIES ON FAILURE")
    print("=" * 60)
    print()
    print("  LiteLLM auto-retries failed calls (network blips, rate limits, etc.)\n")

    messages = [{"role": "user", "content": "Say hello in one word."}]

    # num_retries = how many times to retry before giving up
    # If the LLM fails, LiteLLM waits and retries automatically (exponential backoff)
    print("  Calling with num_retries=3...")
    # Bonus: fallbacks — if primary model fails, use a backup:
    # completion(model='groq/...', fallbacks=['groq/llama-3.1-8b-instant'])
    # → primary fails → automatically tries the fallback model
    try:
        resp = completion(
            model=MODEL,
            messages=messages,
            num_retries=3,          # retry up to 3 times on failure
            timeout=30,   #within 30sec give response else failure
        )
        print(f"    Success: {resp.choices[0].message.content.strip()}")
        print("    (If it had failed, LiteLLM would have retried automatically)")
    except Exception as e:
        print(f"    Failed after retries: {e}")

    # Fallback models: if the primary fails, try a backup model
    print("\n  Bonus: fallbacks — if primary model fails, use a backup:")
    print("    completion(model='groq/...', fallbacks=['groq/llama-3.1-8b-instant'])")
    print("    → primary fails → automatically tries the fallback model\n")


# ============================================================
# 3. RATE LIMITING — cap requests per minute
# ============================================================

def demo_rate_limiting():
    print("=" * 60)
    print("  3. RATE LIMITING")
    print("=" * 60)
    print()
    print("  Cap how many requests go through per time window (respect provider limits).\n")

    # NOTE: LiteLLM's Router has an 'rpm' setting, but within a single process it's
    # used for routing decisions across deployments — it doesn't hard-block reliably
    # in a simple script. The LiteLLM PROXY SERVER enforces rate limits strictly
    # (per API key / per user) using Redis.
    #
    # To SHOW real throttling clearly, here's a simple rate limiter that genuinely
    # blocks — the same logic a proxy uses internally.

    class RateLimiter:
        """Allow at most `max_requests` per `window` seconds. Blocks the rest."""
        def __init__(self, max_requests: int, window_seconds: float):
            self.max_requests = max_requests
            self.window = window_seconds
            self.timestamps = []  # times of recent allowed requests

        def allow(self) -> bool:
            now = time.time()
            # Drop timestamps older than the window
            self.timestamps = [t for t in self.timestamps if now - t < self.window]
            if len(self.timestamps) < self.max_requests:
                self.timestamps.append(now)
                return True
            return False

    # Allow 3 requests per 10 seconds
    limiter = RateLimiter(max_requests=3, window_seconds=10)

    print("  Rate limit: 3 requests per 10 seconds.")
    print("  Sending 5 quick requests — watch requests 4 and 5 get BLOCKED:\n")

    for i in range(1, 6):
        if limiter.allow():
            start = time.time()
            resp = completion(
                model=MODEL,
                messages=[{"role": "user", "content": f"Say the number {i}"}],
            )
            print(f"    Request {i}: OK ({time.time() - start:.2f}s)")
        else:
            # Over the limit — a proxy would queue or reject this
            print(f"    Request {i}: BLOCKED (rate limit hit — 3/10s used)")

    print("\n  Requests 4 and 5 were blocked because we hit 3 requests in the window.")
    print("  A real LLM proxy (LiteLLM proxy server) does this per-user with Redis,")
    print("  so no single client can exceed the provider's rate cap.\n")


# ============================================================
# 4. BUDGET TRACKING — track $ spent, block at limit
# ============================================================

def demo_budget():
    print("=" * 60)
    print("  4. BUDGET TRACKING ($100 limit example)")
    print("=" * 60)
    print()
    print("  Track cost per call. Stop when the budget is used up.\n")

    # We'll track budget ourselves using LiteLLM's cost calculator.
    # (LiteLLM also has a built-in BudgetManager and the proxy server enforces this.)
    BUDGET_LIMIT = 100.00  # $100 total budget
    spent = 0.0

    # ------------------------------------------------------------------
    # IMPORTANT: LiteLLM only auto-calculates cost for models it has in its
    # pricing table. gpt-oss-20b on Groq isn't mapped, so completion_cost()
    # would fail. We register the price manually (per-token, in dollars).
    # Groq gpt-oss-20b pricing (approx): $0.10 / 1M input, $0.50 / 1M output.
    # ------------------------------------------------------------------
    PRICE_PER_INPUT_TOKEN = 0.10 / 1_000_000    # $0.10 per 1M input tokens
    PRICE_PER_OUTPUT_TOKEN = 0.50 / 1_000_000   # $0.50 per 1M output tokens

    def calc_cost(response) -> float:
        """Calculate cost ourselves from token counts (robust fallback)."""
        # First try LiteLLM's built-in calculator
        try:
            return litellm.completion_cost(completion_response=response)
        except Exception:
            # Model not in LiteLLM's pricing table — compute manually
            usage = response.usage
            return (
                usage.prompt_tokens * PRICE_PER_INPUT_TOKEN
                + usage.completion_tokens * PRICE_PER_OUTPUT_TOKEN
            )

    questions = [
        "What is Python?",
        "What is FastAPI?",
        "What is Redis?",
        "What is Docker?",
        "What is Kubernetes?",
    ]

    print(f"  Starting budget: ${BUDGET_LIMIT:.2f}\n")

    for i, q in enumerate(questions, 1):
        # Check budget BEFORE making the call
        if spent >= BUDGET_LIMIT:
            print(f"  Request {i}: BLOCKED — budget exhausted (${spent:.4f} used)")
            continue

        resp = completion(
            model=MODEL,
            messages=[{"role": "user", "content": q}],
        )

        # Calculate the cost of this call
        call_cost = calc_cost(resp)
        spent += call_cost
        remaining = BUDGET_LIMIT - spent

        tokens = resp.usage.total_tokens
        print(f"  Request {i}: '{q}'")
        print(f"    Tokens: {tokens} (in: {resp.usage.prompt_tokens}, out: {resp.usage.completion_tokens})")
        print(f"    Cost: ${call_cost:.6f}")
        print(f"    Spent so far: ${spent:.6f} | Remaining: ${remaining:.4f}")
        print()

    print(f"  Total spent: ${spent:.6f} of ${BUDGET_LIMIT:.2f}")
    print(f"  Remaining: ${BUDGET_LIMIT - spent:.4f}")
    print()
    print("  Note: Groq's gpt-oss models are very cheap, so cost is tiny.")
    print("  The point: track cost per call, so you can enforce a budget and BLOCK")
    print("  requests once the limit is hit — exactly what a proxy does.")
    print()
    print("  Tip: to see BLOCKING happen, set BUDGET_LIMIT very low (e.g. 0.000001).")
    print()


# ============================================================
# RUN ALL
# ============================================================

def main():
    print("\n")
    print("  LiteLLM as an LLM Proxy — Feature Demo")
    print("  Model:", MODEL)
    print()

    demo_caching()
    input("  Press Enter for RETRIES...\n")

    demo_retries()
    input("  Press Enter for RATE LIMITING...\n")

    demo_rate_limiting()
    input("  Press Enter for BUDGET TRACKING...\n")

    demo_budget()

    print("=" * 60)
    print("  DONE! These 4 features are why teams use an LLM proxy.")
    print("=" * 60)


if __name__ == "__main__":
    main()
