"""
Streaming Basics — SSE (Server-Sent Events) with FastAPI

This shows the two approaches to streaming LLM responses to a browser:
1. SSE via StreamingResponse (one-way: server → client)
2. A simple test endpoint that streams fake tokens (no API key needed)

Run:
    cd 10-streaming && ../.venv/bin/python3 02_streaming_basics.py

Then try:
    - http://localhost:8000/stream/fake   (no API key needed, shows the mechanics)
    - http://localhost:8000/stream/chat?message=Explain async in 3 sentences  (real LLM)
    - http://localhost:8000/docs           (interactive API docs)

Key Concept:
    Normal endpoint:   Collect ALL tokens → send as one response (user waits 3-5s)
    Streaming endpoint: Send EACH token as it's generated (user sees words appear)
"""

import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="Streaming Basics", version="1.0.0")

# LLM client
llm_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# 1. FAKE STREAMING (no API key needed — shows the mechanics)
# ============================================================

async def fake_token_generator():
    """
    Simulates an LLM generating tokens one at a time.
    Each token is sent as an SSE event.
    
    SSE format: each event is "data: <content>\n\n"
    Final event: "data: [DONE]\n\n"
    """
    fake_response = "Streaming works by sending each token as it's generated, " \
                    "instead of waiting for the entire response. " \
                    "This makes the UI feel much more responsive, " \
                    "even though the total generation time is the same."
    
    # Simulate token-by-token generation
    words = fake_response.split(" ")
    for i, word in enumerate(words):
        # Add space before word (except first)
        token = f" {word}" if i > 0 else word
        
        # SSE format: "data: <content>\n\n"
        yield f"data: {token}\n\n"
        
        # Simulate LLM thinking time (50-150ms per token)
        await asyncio.sleep(0.08)
    
    # Signal that stream is complete
    yield "data: [DONE]\n\n"


@app.get("/stream/fake")
async def stream_fake():
    """
    Test streaming without an API key.
    Open in browser or use: curl http://localhost:8000/stream/fake
    """
    return StreamingResponse(
        fake_token_generator(),
        media_type="text/event-stream",  # This tells the browser it's a stream
        headers={
            "Cache-Control": "no-cache",         # Don't cache stream
            "Connection": "keep-alive",          # Keep connection open
            "X-Accel-Buffering": "no",           # Disable nginx buffering
        },
    )


# ============================================================
# 2. REAL LLM STREAMING (needs GROQ_API_KEY)
# ============================================================

async def llm_stream_generator(message: str):
    """
    Stream tokens from the actual LLM.
    
    The key difference from non-streaming:
        Non-streaming: response.choices[0].message.content  (complete text)
        Streaming:     chunk.choices[0].delta.content        (one piece at a time)
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": message},
    ]
    
    # stream=True is the magic flag
    stream = await llm_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,  # <-- This changes everything
    )
    
    # Each chunk contains a tiny piece of the response
    async for chunk in stream:
        # chunk.choices[0].delta.content is the new token(s)
        # It can be None for the first/last chunks (role info, finish reason)
        content = chunk.choices[0].delta.content
        if content:
            yield f"data: {content}\n\n"
    
    yield "data: [DONE]\n\n"


@app.get("/stream/chat")
async def stream_chat(message: str = "Explain what streaming is in 2 sentences"):
    """
    Stream a real LLM response.
    Try: http://localhost:8000/stream/chat?message=What is Python?
    """
    return StreamingResponse(
        llm_stream_generator(message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 3. COMPARISON: Non-streaming vs Streaming (same question)
# ============================================================

@app.get("/no-stream/chat")
async def no_stream_chat(message: str = "Explain what streaming is in 2 sentences"):
    """
    Same question, but waits for full response.
    Compare the feel: this endpoint hangs for 2-4 seconds, then shows everything at once.
    """
    response = await llm_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        stream=False,  # Default — wait for everything
    )
    
    return {"answer": response.choices[0].message.content}


# ============================================================
# 4. STREAMING WITH TOKEN COUNTING (accumulate while streaming)
# ============================================================

async def counted_stream_generator(message: str):
    """
    Shows how to accumulate the full response while streaming.
    Useful for: saving to DB, counting tokens, logging.
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": message},
    ]
    
    stream = await llm_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        stream=True,
    )
    
    # Accumulate full response while streaming
    full_response = ""
    token_count = 0
    
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            full_response += content
            token_count += 1  # Approximate: 1 chunk ≈ 1 token
            yield f"data: {content}\n\n"
    
    # Send metadata as final event (before DONE)
    yield f"data: \n\n"
    yield f"data: --- Stats: ~{token_count} tokens, {len(full_response)} chars ---\n\n"
    yield "data: [DONE]\n\n"
    
    # Here you could save full_response to a database
    # await save_to_db(full_response)


@app.get("/stream/counted")
async def stream_counted(message: str = "List 5 Python tips"):
    """Stream with token counting — shows how to accumulate while streaming."""
    return StreamingResponse(
        counted_stream_generator(message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ============================================================
# SIMPLE HTML TEST PAGE
# ============================================================

@app.get("/")
async def home():
    """A minimal page to test streaming visually."""
    return StreamingResponse(
        iter(["""<!DOCTYPE html>
<html>
<head><title>Streaming Basics</title></head>
<body style="font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 20px;">
    <h1>Streaming Basics</h1>
    
    <h3>1. Fake stream (no API key)</h3>
    <button onclick="testStream('/stream/fake')">Run fake stream</button>
    
    <h3>2. Real LLM stream</h3>
    <input id="msg" value="Explain recursion in 3 sentences" style="width:400px; padding:8px;">
    <button onclick="testStream('/stream/chat?message=' + encodeURIComponent(document.getElementById('msg').value))">
        Stream it
    </button>
    
    <h3>3. Non-streaming (compare the feel)</h3>
    <button onclick="testNoStream()">Same question, no stream</button>
    
    <h3>Output:</h3>
    <pre id="output" style="background:#f4f4f4; padding:16px; border-radius:8px; white-space:pre-wrap; min-height:80px;"></pre>
    
    <script>
    async function testStream(url) {
        const output = document.getElementById('output');
        output.textContent = '';
        
        const response = await fetch(url);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            // Parse SSE: each line starts with "data: "
            const lines = text.split('\\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const token = line.slice(6);  // Remove "data: " prefix
                    if (token === '[DONE]') break;
                    output.textContent += token;
                }
            }
        }
    }
    
    async function testNoStream() {
        const output = document.getElementById('output');
        const msg = document.getElementById('msg').value;
        output.textContent = 'Waiting for full response...';
        
        const res = await fetch('/no-stream/chat?message=' + encodeURIComponent(msg));
        const data = await res.json();
        output.textContent = data.answer;
    }
    </script>
</body>
</html>"""]),
        media_type="text/html",
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  Streaming Basics")
    print("=" * 50)
    print()
    print("  Home:     http://localhost:8000")
    print("  Fake:     http://localhost:8000/stream/fake")
    print("  Real:     http://localhost:8000/stream/chat?message=Hello")
    print("  Counted:  http://localhost:8000/stream/counted?message=Hello")
    print("  No-stream: http://localhost:8000/no-stream/chat?message=Hello")
    print("  Docs:     http://localhost:8000/docs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
