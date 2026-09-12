"""
Streaming Utilities — Reusable helpers for streaming patterns.

These are the building blocks you'll use in any streaming app.
"""

import os
import time
import asyncio
from typing import AsyncGenerator
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# ============================================================
# LLM CLIENT SETUP
# ============================================================

def get_llm_client() -> AsyncOpenAI:
    """Create an async LLM client (Groq)."""
    return AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


DEFAULT_MODEL = "openai/gpt-oss-20b"


# ============================================================
# STREAMING GENERATORS
# ============================================================

async def stream_completion(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from the LLM as an async generator.
    
    Usage:
        async for token in stream_completion(messages):
            print(token, end="", flush=True)
    
    This is the core pattern — everything else builds on top of this.
    """
    client = get_llm_client()
    
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content


async def stream_with_accumulator(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Stream tokens AND accumulate the full response.
    
    Yields (token, full_response_so_far) tuples.
    
    Usage:
        async for token, full in stream_with_accumulator(messages):
            print(token, end="")
        print(f"\\nFull response: {full}")
    """
    full_response = ""
    
    async for token in stream_completion(messages, model, temperature):
        full_response += token
        yield token, full_response


# ============================================================
# SSE FORMATTING
# ============================================================

def format_sse(data: str, event: str | None = None) -> str:
    """
    Format data as a Server-Sent Event.
    
    SSE format:
        event: <event_name>\\n   (optional)
        data: <content>\\n
        \\n                       (blank line = end of event)
    """
    lines = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {data}")
    lines.append("")  # Blank line terminates the event
    return "\n".join(lines) + "\n"


async def sse_stream_generator(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
) -> AsyncGenerator[str, None]:
    """
    Ready-to-use SSE generator for FastAPI StreamingResponse.
    
    Usage:
        from fastapi.responses import StreamingResponse
        
        return StreamingResponse(
            sse_stream_generator(messages),
            media_type="text/event-stream",
        )
    """
    async for token in stream_completion(messages, model):
        yield format_sse(token)
    
    yield format_sse("[DONE]")


# ============================================================
# TIMING UTILITY
# ============================================================

class StreamTimer:
    """
    Measure streaming performance.
    
    Usage:
        timer = StreamTimer()
        async for token in stream_completion(messages):
            timer.token_received()
            print(token, end="")
        timer.done()
        print(timer.summary())
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.first_token_time = None
        self.token_count = 0
        self.end_time = None
    
    def token_received(self):
        if self.first_token_time is None:
            self.first_token_time = time.time()
        self.token_count += 1
    
    def done(self):
        self.end_time = time.time()
    
    @property
    def time_to_first_token(self) -> float:
        """Seconds until first token arrived (TTFT)."""
        if self.first_token_time is None:
            return 0
        return self.first_token_time - self.start_time
    
    @property
    def total_time(self) -> float:
        """Total seconds from start to last token."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def tokens_per_second(self) -> float:
        """Average generation speed."""
        if self.total_time == 0:
            return 0
        return self.token_count / self.total_time
    
    def summary(self) -> str:
        return (
            f"\n--- Stream Stats ---\n"
            f"  Time to first token: {self.time_to_first_token:.3f}s\n"
            f"  Total time: {self.total_time:.3f}s\n"
            f"  Tokens: {self.token_count}\n"
            f"  Speed: {self.tokens_per_second:.1f} tokens/sec\n"
        )


# ============================================================
# DEMO: Run this file directly to test streaming in terminal
# ============================================================

async def demo():
    """Quick terminal demo of streaming."""
    print("=" * 50)
    print("  Streaming Demo (terminal)")
    print("=" * 50)
    print()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": "Explain WebSockets in 3 sentences."},
    ]
    
    print("Question: Explain WebSockets in 3 sentences.\n")
    print("Answer: ", end="", flush=True)
    
    timer = StreamTimer()
    
    async for token in stream_completion(messages):
        timer.token_received()
        print(token, end="", flush=True)
    
    timer.done()
    print(timer.summary())


if __name__ == "__main__":
    asyncio.run(demo())
