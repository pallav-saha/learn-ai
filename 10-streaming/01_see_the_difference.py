"""
See the Difference: Streaming vs Non-Streaming

Run this and WATCH your terminal. You'll see:
1. Non-streaming: nothing... nothing... nothing... BOOM full answer appears
2. Streaming: words appear one by one in real time

Run:
    cd 10-streaming && ../.venv/bin/python3 01_see_the_difference.py
"""

import os
import sys
import time
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Setup
client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

QUESTION = "Explain what Python is in 4 sentences."

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": QUESTION},
]


# ============================================================
# 1. WITHOUT STREAMING (how module 09 works)
# ============================================================

async def without_streaming():
    """
    The old way. You wait. And wait. Then get everything at once.
    """
    print("=" * 60)
    print("  1. WITHOUT STREAMING")
    print("=" * 60)
    print(f"\n  Question: {QUESTION}\n")
    print("  Waiting for full response", end="")

    start = time.time()

    # This call BLOCKS until the ENTIRE response is ready
    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        stream=False,  # <-- No streaming. Wait for everything.
    )

    elapsed = time.time() - start

    # You get the answer only AFTER the LLM finishes generating ALL tokens
    answer = response.choices[0].message.content

    print(f" (waited {elapsed:.2f}s)\n")
    print(f"  Answer: {answer}")
    print(f"\n  You saw NOTHING for {elapsed:.2f}s, then the full answer appeared.")
    print()


# ============================================================
# 2. WITH STREAMING (the new way)
# ============================================================

async def with_streaming():
    """
    The new way. Each token appears as it's generated.
    Watch your terminal — words will appear one by one.
    """
    print("=" * 60)
    print("  2. WITH STREAMING")
    print("=" * 60)
    print(f"\n  Question: {QUESTION}\n")
    print("  Answer: ", end="")
    sys.stdout.flush()

    start = time.time()
    first_token_time = None
    token_count = 0
    full_response = ""

    # This returns IMMEDIATELY — gives you a stream (a tap)
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,  # <-- Streaming ON. Get tokens as they come.
    )

    # Loop through tokens as they arrive
    async for chunk in stream:
        # chunk.choices[0].delta.content = just the new token
        content = chunk.choices[0].delta.content

        if content:
            if first_token_time is None:
                first_token_time = time.time()

            token_count += 1
            full_response += content

            # Print each token IMMEDIATELY (this is what the browser does)
            print(content, end="")
            sys.stdout.flush()  # Force display without waiting for newline

    elapsed = time.time() - start
    ttft = (first_token_time - start) if first_token_time else 0

    print(f"\n")
    print(f"  First token appeared after: {ttft:.3f}s (Time To First Token)")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Tokens received: {token_count}")
    print(f"  Speed: {token_count / elapsed:.0f} tokens/sec")
    print(f"\n  You saw the FIRST word in {ttft:.3f}s, not {elapsed:.2f}s!")
    print()


# ============================================================
# 3. BONUS: See what a chunk actually looks like
# ============================================================

async def inspect_chunks():
    """
    Print the raw chunks so you can see the actual data structure.
    """
    print("=" * 60)
    print("  3. WHAT CHUNKS LOOK LIKE (raw data)")
    print("=" * 60)
    print(f"\n  Showing first 5 chunks from the API:\n")

    stream = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Say hello world"},
        ],
        temperature=0.0,
        stream=True,
    )

    count = 0
    async for chunk in stream:
        count += 1
        delta = chunk.choices[0].delta
        finish = chunk.choices[0].finish_reason

        print(f"  Chunk {count}:")
        print(f"    delta.role    = {getattr(delta, 'role', None)}")
        print(f"    delta.content = {repr(delta.content)}")
        print(f"    finish_reason = {finish}")
        print()

        if count >= 8:
            print("  ... (showing first 8 only)")
            break

    print()


# ============================================================
# RUN ALL
# ============================================================

async def main():
    print("\n")

    # First: the old way (boring wait)
    await without_streaming()

    input("  Press Enter to see streaming...\n")

    # Second: the new way (tokens appear live)
    await with_streaming()

    input("  Press Enter to see raw chunk data...\n")

    # Third: peek under the hood
    await inspect_chunks()

    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("""
  Without streaming:
    - You wait 2-5 seconds seeing NOTHING
    - Then the full answer appears at once
    - response.choices[0].message.content = "full answer"

  With streaming:
    - First word appears in ~0.2 seconds
    - Words keep appearing one by one
    - chunk.choices[0].delta.content = "one word"

  Same answer. Same cost. Same tokens.
  The ONLY difference is when you see them.
""")


if __name__ == "__main__":
    asyncio.run(main())
