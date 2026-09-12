"""
Advanced Streaming Concepts

This file teaches 5 advanced topics you'll encounter in production streaming:
1. Backpressure — what if consumer is slower than producer?
2. Retry/Resume — what if the connection drops mid-stream?
3. Server-side buffering — why streams get "stuck" behind Nginx/CloudFront
4. Streaming structured output — getting JSON piece by piece
5. Multiple concurrent streams — handling many users at once

Run:
    cd 10-streaming && ../.venv/bin/python3 05_advanced_streaming.py
"""

import os
import json
import asyncio
import time
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# 1. BACKPRESSURE
# ============================================================
# What: Producer (LLM) generates tokens faster than consumer (browser) can handle.
# When: Rare with LLMs (they're slow ~50-100 tokens/sec). Common with video streaming.
# Problem: If browser renders at 10 tokens/sec but LLM sends 100 tokens/sec,
#          tokens pile up in memory → memory leak → crash.
# Solution: Buffer with a max size. If buffer is full, slow down the producer.

async def demo_backpressure():
    """
    Shows backpressure using an asyncio.Queue with a max size.
    
    Think of it like a pipe:
    - Producer pours water in (tokens from LLM)
    - Consumer drinks from the other end (browser rendering)
    - If pipe is full, producer MUST WAIT (backpressure)
    """
    print("=" * 60)
    print("  1. BACKPRESSURE")
    print("=" * 60)
    print()
    print("  Problem: Producer is faster than consumer.")
    print("  Solution: Queue with max size. Producer waits when full.\n")

    # Queue with max size 3 — can only hold 3 tokens at a time
    # If full, producer blocks until consumer takes one out
    buffer = asyncio.Queue(maxsize=3)

    async def fast_producer():
        """LLM generating tokens fast (simulated)."""
        tokens = ["Hello", " world", "!", " This", " is", " streaming", "."]
        for token in tokens:
            await asyncio.sleep(0.1)  # Fast: 100ms per token
            # If the queue has space → puts it instantly, continues
            # If the queue is full (already has 3 items) → pauses here and waits until the consumer takes one out
            await buffer.put(token)   # If buffer full, THIS LINE WAITS (backpressure!)
            # qsize() shows the queue size AFTER the put, but timing between producer (100ms) and consumer (400ms) means the consumer sometimes grabs a token before the next print.
            print(f"    Producer: sent '{token}' (queue size: {buffer.qsize()})")
        await buffer.put(None)  # Signal: no more tokens

    async def slow_consumer():
        """Browser rendering tokens slowly (simulated)."""
        result = ""
        while True:
            # Take one token out of the queue. If the queue is empty, wait until the producer puts something in.
            token = await buffer.get()  # Wait for next token
            if token is None:
                break
            await asyncio.sleep(0.4)  # Slow: 400ms to render each token
            result += token
            print(f"    Consumer: rendered '{token}' → '{result}'")
        print(f"\n    Final: '{result}'")

    start = time.time()
    # Run both at the same time
    await asyncio.gather(fast_producer(), slow_consumer())
    print(f"\n  Total time: {time.time() - start:.1f}s")
    print("  Notice: producer had to WAIT when queue was full (size 3).")
    print("  Without backpressure: tokens would pile up in memory forever.")
    print()
    """
    Producer sends "Hello"    (queue: 1)  ← fast
    Producer sends " world"   (queue: 2)  ← fast
    Producer sends "!"        (queue: 3)  ← fast, queue now FULL
    Producer tries " This"    → BLOCKED! waits... (queue full)
    Consumer renders "Hello"  (queue: 2)  ← took 400ms, freed a slot
    Producer sends " This"    (queue: 3)  ← now unblocked, queue full again
    Producer tries " is"      → BLOCKED! waits...
    Consumer renders " world" (queue: 2)  ← freed a slot
    ...and so on

    The producer keeps hitting the wall at size 3 and waiting. The queue never grows beyond 3 items in memory.

    Why this matters:
    Without the maxsize=3 limit:

    python

    buffer = asyncio.Queue()  # unlimited
    The fast producer would dump all 7 tokens in instantly while the slow consumer is still rendering the first one. With 7 tokens that's fine. But with a real LLM generating 1000 tokens while the browser lags, they'd pile up in memory — potentially gigabytes — and crash the app.

    The maxsize forces the producer to wait, keeping memory bounded. That's backpressure: the slow consumer "pushes back" on the fast producer.
    """

# ============================================================
# 2. RETRY / RESUME
# ============================================================
# What: Connection drops mid-stream. You want to continue, not restart.
# When: Mobile users, flaky wifi, long responses.
# Problem: If stream dies at token 50 of 200, user loses all progress.
# Solution: Save progress server-side. On reconnect, send remaining tokens.

async def demo_retry_resume():
    """
    Shows how to implement retry/resume for streaming.
    
    Pattern:
    1. Assign each stream a unique ID
    2. Save tokens server-side as they're generated
    3. On reconnect, client sends "I got up to token X"
    4. Server resends from token X+1
    """
    print("=" * 60)
    print("  2. RETRY / RESUME")
    print("=" * 60)
    print()
    print("  Problem: Connection drops mid-stream. Don't want to re-generate.\n")

    # Server-side storage (in production: Redis or database)
    stream_storage: dict[str, list] = {}

    async def generate_and_store(stream_id: str, question: str):
        """Generate tokens and store them server-side."""
        # Simulate LLM generating tokens
        answer = "Python is a versatile programming language used for web development AI and automation"
        tokens = answer.split(" ")

        stream_storage[stream_id] = []  # Initialize storage

        for i, token in enumerate(tokens):
            await asyncio.sleep(0.1)
            stored_token = {"index": i, "content": f" {token}" if i > 0 else token}
            stream_storage[stream_id].append(stored_token)
            yield stored_token

    async def resume_from(stream_id: str, last_received_index: int):
        """Resume sending tokens from where the client left off."""
        stored = stream_storage.get(stream_id, [])
        for token in stored:
            if token["index"] > last_received_index:
                yield token

    # --- Simulate: connection works for first 5 tokens, then drops ---
    stream_id = "stream_abc123"
    print(f"  Stream ID: {stream_id}")
    print(f"  First connection (gets 5 tokens, then drops):\n")

    last_index = -1
    async for token in generate_and_store(stream_id, "What is Python?"):
        print(f"    Got token {token['index']}: '{token['content']}'")
        last_index = token["index"]
        if last_index == 4:
            print("    ❌ CONNECTION DROPPED!\n")
            break

    # --- Client reconnects and says "I got up to index 4" ---
    print(f"  Reconnecting... last received index: {last_index}")
    print(f"  Resuming from index {last_index + 1}:\n")

    # Wait for the rest to be generated (simulating server still generating)
    # In real life, generation continues server-side even if client disconnects
    remaining_tokens = stream_storage[stream_id][last_index + 1:]

    if remaining_tokens:
        for token in remaining_tokens:
            print(f"    Resumed token {token['index']}: '{token['content']}'")
    else:
        print("    (Generation was only partially done. In production, server")
        print("     continues generating and client gets remaining on reconnect.)")

    # Show the full result
    full = "".join(t["content"] for t in stream_storage[stream_id])
    print(f"\n  Full response: '{full}'")
    print()
    print("  Key insight: Server stores tokens. Client tracks last index.")
    print("  On reconnect: client says 'I have up to X', server sends X+1 onward.")
    print()


# ============================================================
# 3. SERVER-SIDE BUFFERING
# ============================================================
# What: Your stream works locally but gets "stuck" when deployed behind Nginx/CloudFront.
# When: Deploying to production with a reverse proxy.
# Problem: Nginx/CloudFront buffers the response — collects ALL chunks,
#          then sends them at once. Defeats the purpose of streaming!
# Solution: Disable buffering with headers.

async def demo_server_buffering():
    """
    Explains why streaming breaks behind Nginx and how to fix it.
    (No live demo — this is a deployment concept.)
    """
    print("=" * 60)
    print("  3. SERVER-SIDE BUFFERING")
    print("=" * 60)
    print("""
  THE PROBLEM:
  ============
  Your streaming works perfectly on localhost.
  You deploy behind Nginx/CloudFront/ALB.
  Suddenly: user waits 5 seconds, then ALL tokens appear at once.
  
  WHY:
  ====
  Reverse proxies BUFFER responses by default:
  
    LLM → Your Server → [Nginx BUFFERS ALL CHUNKS] → Browser
                         ↑ collects everything first
  
  Nginx thinks: "Let me collect the full response for efficiency."
  This destroys streaming!

  THE FIX:
  ========
  Add these headers to your StreamingResponse:

    headers = {
        "Cache-Control": "no-cache",          # Don't cache
        "Connection": "keep-alive",           # Keep connection open
        "X-Accel-Buffering": "no",            # Tell Nginx: DON'T buffer!
        "Content-Type": "text/event-stream",  # SSE content type
    }

  For Nginx config (nginx.conf), also add:
  
    proxy_buffering off;        # Disable buffering for this route
    proxy_cache off;            # No caching
    proxy_read_timeout 3600;    # Don't timeout long streams

  For AWS ALB/CloudFront:
    - ALB: works with chunked transfer encoding (default)
    - CloudFront: Use "Managed-CachingDisabled" policy
    - API Gateway: Does NOT support streaming (use ALB instead)

  For Vercel/Railway/Render:
    - Usually work out of the box with SSE
    - Set response timeout high enough for long generations

  SUMMARY:
  ========
  If streaming works locally but not in production:
    1. Check reverse proxy buffering (X-Accel-Buffering: no)
    2. Check CDN caching (disable for stream endpoints)
    3. Check timeouts (streams can last 30+ seconds)
""")


# ============================================================
# 4. STREAMING STRUCTURED OUTPUT (JSON)
# ============================================================
# What: You want the LLM to return JSON, but streamed piece by piece.
# When: Building UIs that show partial results (e.g., streaming a list of items).
# Problem: Incomplete JSON is invalid — can't parse "{"name": "Py" until it's complete.
# Solution: Accumulate and try to parse, OR use JSON streaming parsers.

async def demo_streaming_json():
    """
    Shows how to handle streaming when you expect JSON output.
    """
    print("=" * 60)
    print("  4. STREAMING STRUCTURED OUTPUT (JSON)")
    print("=" * 60)
    print()
    print("  Problem: LLM returns JSON, but it arrives token by token.")
    print("  You can't parse incomplete JSON.\n")

    # Simulate LLM streaming JSON token by token
    json_tokens = [
        '{', '\n', '  ', '"name"', ':', ' "', 'Python', '"', ',',
        '\n', '  ', '"year"', ':', ' ', '1991', ',',
        '\n', '  ', '"creator"', ':', ' "', 'Guido', ' van', ' Rossum', '"', ',',
        '\n', '  ', '"uses"', ':', ' [', '"web"', ',', ' "', 'AI', '"', ',', ' "', 'automation', '"', ']',
        '\n', '}'
    ]

    print("  Method 1: ACCUMULATE AND PARSE AT END")
    print("  " + "-" * 45)
    accumulated = ""
    for token in json_tokens:
        accumulated += token
        # Show partial (can't parse yet)
        if len(accumulated) < 40:
            print(f"    So far: {repr(accumulated)} ← can't parse yet")

    # Now parse the complete JSON
    result = json.loads(accumulated)
    print(f"    ...\n    Complete! Parsed: {result}\n")

    # Method 2: Parse partial objects as they become complete
    print("  Method 2: PARSE PARTIAL OBJECTS (extract as you go)")
    print("  " + "-" * 45)
    accumulated = ""
    found_fields = {}

    for token in json_tokens:
        accumulated += token

        # Try to extract key-value pairs as they complete
        # Simple approach: look for "key": "value" patterns
        try:
            # Try parsing — will fail until JSON is complete
            partial = json.loads(accumulated + "}")  # Add closing brace to try
            for key, val in partial.items():
                if key not in found_fields:
                    found_fields[key] = val
                    print(f"    Found field! {key} = {val}")
        except (json.JSONDecodeError, ValueError):
            pass

    print(f"\n    All fields extracted as they arrived!")
    print()

    # Method 3: Best practice — ask LLM for line-by-line format
    print("  Method 3: BEST PRACTICE — Ask for newline-delimited format")
    print("  " + "-" * 45)
    print("""
    Instead of asking for a JSON blob, ask the LLM to return one item per line.
    Each line is independently parseable — no waiting for complete JSON.
    This is how most production apps handle streaming structured data.

    Below is a REAL example: streaming from the LLM and parsing each
    line the moment it completes (when we see a newline).
""")

    # Ask the LLM to return one item per line
    messages = [
        {"role": "system", "content": "You output ONLY the requested format. No extra text."},
        {
            "role": "user",
            "content": (
                "List 5 uses of Python. One per line. "
                "Format each line exactly as: use_name | description"
            ),
        },
    ]

    stream = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3,
        stream=True,
    )

    # Buffer holds the current (incomplete) line as tokens arrive
    line_buffer = ""
    parsed_items = []

    print("    Parsing lines as they complete:\n")

    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if not content:
            continue

        line_buffer += content

        # A newline means the current line is COMPLETE — parse it now
        while "\n" in line_buffer:
            # Split off the first complete line
            line, line_buffer = line_buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            # Parse the line (format: "use_name | description")
            if "|" in line:
                name, _, description = line.partition("|")
                item = {"use": name.strip(), "description": description.strip()}
                parsed_items.append(item)
                # We can act on this item IMMEDIATELY — no waiting for the rest
                print(f"    ✓ Parsed item {len(parsed_items)}: {item['use']}")
                print(f"        → {item['description']}")

    # Handle any leftover text after the last newline
    leftover = line_buffer.strip()
    if leftover and "|" in leftover:
        name, _, description = leftover.partition("|")
        item = {"use": name.strip(), "description": description.strip()}
        parsed_items.append(item)
        print(f"    ✓ Parsed item {len(parsed_items)}: {item['use']}")
        print(f"        → {item['description']}")

    print(f"\n    Done! Parsed {len(parsed_items)} items — each one usable")
    print(f"    the instant its line arrived, not after the full response.")
    print()


# ============================================================
# 5. MULTIPLE CONCURRENT STREAMS
# ============================================================
# What: Handling many users streaming at the same time.
# When: Your app has more than ~10 concurrent users.
# Problem: Each stream holds an open connection and memory.
# Solution: Connection limits, timeouts, and resource management.

async def demo_concurrent_streams():
    """
    Shows how multiple users stream simultaneously and the scaling concerns.
    """
    print("=" * 60)
    print("  5. MULTIPLE CONCURRENT STREAMS (Scaling)")
    print("=" * 60)
    print()
    print("  Simulating 10 users streaming at the same time...\n")

    # Track resources
    active_connections = 0
    max_connections = 0
    total_tokens_sent = 0

    async def simulate_user(user_id: int, num_tokens: int, speed: float):
        """Simulate one user's streaming session."""
        nonlocal active_connections, max_connections, total_tokens_sent

        active_connections += 1
        max_connections = max(max_connections, active_connections)

        for i in range(num_tokens):
            await asyncio.sleep(speed)  # Simulate token generation
            total_tokens_sent += 1

        active_connections -= 1
        return f"User {user_id}: done ({num_tokens} tokens)"

    # 10 users, different response lengths
    start = time.time()
    results = await asyncio.gather(*[
        simulate_user(i + 1, num_tokens=5 + i * 2, speed=0.05)
        for i in range(10)
    ])

    elapsed = time.time() - start

    for r in results:
        print(f"    {r}")

    print(f"\n  --- Stats ---")
    print(f"  Total time: {elapsed:.1f}s (all 10 users served concurrently!)")
    print(f"  Peak concurrent connections: {max_connections}")
    print(f"  Total tokens sent: {total_tokens_sent}")
    print(f"  If sequential: would have taken ~{total_tokens_sent * 0.05:.1f}s")
    print()

    print("  SCALING CONCERNS:")
    print("  " + "-" * 45)
    print("""
    1. MEMORY: Each connection holds conversation history in RAM.
       - 100 users × 20 messages × ~500 chars = ~1MB (fine)
       - 10,000 users × 20 messages = ~100MB (need Redis/DB instead of dict)

    2. CONNECTIONS: Each WebSocket/SSE holds a TCP connection open.
       - Linux default: 1024 max open files per process
       - Fix: ulimit -n 65535 (increase limit)
       - Or use multiple server processes behind a load balancer

    3. LLM API RATE LIMITS: Groq/OpenAI have rate limits.
       - Groq free tier: ~30 requests/minute
       - Solution: Queue requests, retry with backoff, or upgrade plan

    4. TIMEOUT: Long responses can hit timeouts.
       - Nginx default: 60s proxy timeout
       - Fix: proxy_read_timeout 300; (increase)
       - Or implement heartbeat pings to keep connection alive

    5. GRACEFUL SHUTDOWN: When restarting server, don't kill active streams.
       - Drain existing connections (stop accepting new ones)
       - Wait for active streams to finish (with a deadline)
       - Then shut down

    ARCHITECTURE FOR SCALE:
    =======================
    
    Small (< 100 users):
      Single FastAPI server. Dict for conversations. Direct LLM calls.
      "Dict for conversations" means storing each user's chat history in a Python dictionary in the server's memory (RAM) where application is deployed — keyed by user/session ID.
      When you write a variable at the top of your FastAPI file, that variable IS stored in the server's RAM.
      That conversations = {} dictionary sits in your computer's memory (RAM) the whole time uvicorn is running. Every request reads from and writes to it.
      RAM = your computer's temporary working memory. When your Python program runs, all its variables live in RAM.
      That's the catch: restart the server, and the dict is empty again. All conversations vanish because RAM doesn't persist.

      So the direct answer: in FastAPI, you store conversations in a module-level variable (dict in RAM) for simple cases, or in a database/Redis when you need them to persist and be shared. You're already using the RAM approach in module 09.

    Medium (100-10,000 users):
      Multiple FastAPI workers (gunicorn/uvicorn workers).
      Redis for shared conversation state.
      Queue for LLM requests (celery/bull).

      Redis for shared conversation state meaning, It's needed because of load balancing. When you have multiple server copies, a single user's requests get spread across different servers.
      The problem: Single user next requests rotated across Server-1, Server-2, Server-3. so if first question, my name is pallab goes to server1 and next question whats my name? goes to server 2 it cannot answer, as conversation is stored in server 1 ram and not server 2 ram. also if fast api restarts then the ram conversation data is lost.
      The user's history is stuck on Server-1, but their second message landed on Server-2 which never saw it. The conversation is broken.
      
      The fix — one shared store (Redis/database):
      Message 1 → Server-1 → writes to Redis
      Message 2 → Server-2 → reads from Redis → sees msg1! → "Your name is Pallab"

      Option B: Sticky sessions — the simpler workaround
      Configure Nginx (ip_hash) so a user ALWAYS hits the same server
      Then that server's dict always has their history.
      Downside of sticky sessions: if that one server dies, the user loses their history anyway. Shared store (Redis) doesn't have this problem.

      "Shared across servers" is needed because load balancing spreads one user's requests across multiple servers.

      Summary: Multiple FastAPI workers (gunicorn/uvicorn workers).
        You have 1 FastAPI app. Running uvicorn app:app --workers 4 tells uvicorn to fork itself into 4 identical worker processes that share one port. The OS distributes requests among them. Why? To use multiple CPU cores (Python's GIL limits one process to one core). The tradeoff: each worker has separate RAM, so shared state (conversations) must move to Redis/DB.

        A queue for LLM requests means: instead of your web server calling the LLM directly and making the user wait, you put the request in a line (queue), and separate worker processes pick them up one at a time. Let me explain why and how.
        This is fine for a few users. But it breaks down when:

        1. LLM rate limits. Groq free tier allows ~30 requests/minute. If 100 users hit you at once, requests 31-100 fail with "rate limit exceeded."

        2. Long tasks block things. Some LLM tasks take 30+ seconds (generating a long document, processing many chunks). The user's HTTP connection sits there waiting, might time out.

        3. Traffic spikes. 500 users arrive at once. Your server can't call the LLM 500 times simultaneously.

        The analogy — a restaurant:

        Without queue:
        Customer orders → waiter runs to kitchen, cooks it himself, brings it back
        → waiter can only serve ONE customer at a time. Chaos at rush hour.

        With queue:
        Customer orders → waiter writes ticket, pins it to the rail (queue)
        → chefs pull tickets and cook at their own pace
        → waiter is free to take more orders immediately

        Celery — the Python one. You define tasks, Celery handles queuing them and running them on worker processes.

    Large (10,000+ users):
      Load balancer → Multiple servers.
      Redis/PostgreSQL for state.
      Dedicated LLM proxy with rate limiting.
      WebSocket sticky sessions (user always hits same server).

      Simplest way to decide:
        Ask: "Can I split this work into independent pieces?"

        Yes → horizontal (more tasks/workers, each does a piece)
        No, it's one big indivisible thing → vertical (one bigger machine)

        --------
        A dedicated LLM proxy is a single service that ALL your servers call to reach the LLM — instead of each server calling the LLM API directly. It centralizes control over your LLM usage.
        Problems:
        Rate limits: Groq allows, say, 30 requests/min. But 10 servers each sending 10/min = 100/min total → you get blocked.
        No central control: can't track total spend, can't prioritize, can't switch providers easily.
        API keys everywhere: every server needs the secret key.



""")


# ============================================================
# RUN ALL
# ============================================================

async def main():
    print("\n")

    await demo_backpressure()
    input("  Press Enter for next topic...\n")

    await demo_retry_resume()
    input("  Press Enter for next topic...\n")

    await demo_server_buffering()
    input("  Press Enter for next topic...\n")

    await demo_streaming_json()
    input("  Press Enter for next topic...\n")

    await demo_concurrent_streams()

    print("=" * 60)
    print("  DONE! You now know production-level streaming.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
