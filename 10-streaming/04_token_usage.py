"""
Token Usage — See exactly how many tokens are sent and received.

Shows:
1. Non-streaming: token count from response object
2. Streaming: token count from last chunk (with stream_options)
3. Cost estimation based on token usage

Run:
    cd 10-streaming && ../.venv/bin/python3 04_token_usage.py
"""

import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# 1. NON-STREAMING: Token usage is in the response
# ============================================================

async def token_usage_no_stream():
    """Token usage without streaming — simplest way."""
    print("=" * 55)
    print("  1. Token Usage — Non-Streaming")
    print("=" * 55)

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": "What is Python? Answer in 2 sentences."},
    ]

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
    )

    answer = response.choices[0].message.content

    print(f"\n  Question: What is Python? Answer in 2 sentences.")
    print(f"  Answer:   {answer}\n")
    print(f"  --- Token Usage ---")
    print(f"  Input tokens (what you SENT):       {response.usage.prompt_tokens}")
    print(f"  Output tokens (what you RECEIVED):  {response.usage.completion_tokens}")
    print(f"  Total tokens:                       {response.usage.total_tokens}")
    print()
    print(f"  Breakdown:")
    print(f"    System prompt + your question = {response.usage.prompt_tokens} tokens (input)")
    print(f"    LLM's answer                  = {response.usage.completion_tokens} tokens (output)")
    print(f"    You pay for both              = {response.usage.total_tokens} tokens total")
    print()


# ============================================================
# 2. STREAMING: Token usage comes in the last chunk
# ============================================================

async def token_usage_streaming():
    """Token usage with streaming — need stream_options."""
    print("=" * 55)
    print("  2. Token Usage — Streaming")
    print("=" * 55)

    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": "What is Python? Answer in 2 sentences."},
    ]

    # Key: add stream_options to get usage in streaming mode
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,
        stream_options={"include_usage": True},  # ← This enables usage in streaming
    )

    print(f"\n  Question: What is Python? Answer in 2 sentences.")
    print(f"  Answer:   ", end="")

    token_count = 0
    usage = None

    async for chunk in stream:
        # Regular chunks have content
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
            token_count += 1

        # The LAST chunk has usage info (when stream_options is set)
        # hasattr(chunk, 'usage')  →  True or False
        # hasattr(chunk, 'usage') means "does this chunk object have a property called usage?"
        if hasattr(chunk, 'usage') and chunk.usage is not None:
            usage = chunk.usage

    print(f"\n")

    if usage:
        print(f"  --- Token Usage ---")
        print(f"  Input tokens (what you SENT):       {usage.prompt_tokens}")
        print(f"  Output tokens (what you RECEIVED):  {usage.completion_tokens}")
        print(f"  Total tokens:                       {usage.total_tokens}")
        print(f"\n  Chunks received: {token_count}")
        print(f"  (Each chunk ≈ 1 token, actual: {usage.completion_tokens} tokens)")
    else:
        print(f"  Usage not available (model may not support stream_options)")
        print(f"  Chunks received: {token_count} (approximate token count)")

    print()


# ============================================================
# 3. TOKEN COMPARISON: Short vs Long prompts
# ============================================================

async def token_comparison():
    """Compare token usage across different prompt lengths."""
    print("=" * 55)
    print("  3. Token Comparison — Short vs Long Prompts")
    print("=" * 55)
    print()

    prompts = [
        ("Short", "Hi"),
        ("Medium", "Explain Python in 2 sentences"),
        ("Long", "Write a detailed explanation of how Python's garbage collector works, including reference counting and generational collection"),
    ]

    for label, prompt in prompts:
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": prompt},
        ]

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=100,  # Limit output for comparison
        )

        u = response.usage
        print(f"  [{label}] \"{prompt[:50]}{'...' if len(prompt) > 50 else ''}\"")
        print(f"    Input: {u.prompt_tokens} tokens | Output: {u.completion_tokens} tokens | Total: {u.total_tokens}")
        print()

    print("  Key Insight:")
    print("    Longer system prompts/questions = more input tokens = more cost")
    print("    You pay for EVERY token in the messages list (system + history + question)")
    print()


# ============================================================
# 4. WHAT COUNTS AS TOKENS?
# ============================================================

async def token_explainer():
    """Show how text maps to tokens."""
    print("=" * 55)
    print("  4. What Counts as Tokens?")
    print("=" * 55)
    print("""
  Rule of thumb:
    1 token ≈ 4 characters in English
    1 token ≈ 0.75 words

  Examples:
    "Hello"           → 1 token
    "Hello world"     → 2 tokens
    "I love Python"   → 3 tokens
    "Pneumonoultramicroscopicsilicovolcanoconiosis" → 10+ tokens (long word = many tokens)

  What costs input tokens:
    - System prompt (sent EVERY time)
    - Conversation history (all previous messages)
    - Your current question
    - Context injected (RAG chunks, etc.)

  What costs output tokens:
    - The LLM's response (every word it generates)

  Why this matters:
    - If your system prompt is 500 tokens, you pay 500 tokens on EVERY message
    - If you send 20 messages of history, you pay for ALL of them each time
    - This is why trimming history (last 10 messages) saves money
""")


# ============================================================
# RUN ALL
# ============================================================

async def main():
    print("\n")
    await token_usage_no_stream()
    input("  Press Enter to continue...\n")

    await token_usage_streaming()
    input("  Press Enter to continue...\n")

    await token_comparison()
    input("  Press Enter to continue...\n")

    await token_explainer()


if __name__ == "__main__":
    asyncio.run(main())
