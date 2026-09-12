# 10 - Streaming + WebSockets

## What's in this folder
- `02_streaming_basics.py` — SSE (Server-Sent Events) streaming with FastAPI
- `03_websocket_chat.py` — WebSocket-based streaming chat (full app with UI)
- `static/index.html` — Browser UI that shows tokens arriving in real-time

## Run

```bash
# Basic SSE streaming demo
cd 10-streaming && ../.venv/bin/python3 02_streaming_basics.py

# Full WebSocket chat (with UI)
cd 10-streaming && ../.venv/bin/python3 03_websocket_chat.py
```

Then visit: http://localhost:8000

## Key Q&A

**Why does ChatGPT show words appearing one by one?**
That's streaming. Instead of waiting 5 seconds for the full answer, the server sends each token (word/piece) as it's generated. The UI renders them immediately. Same total time, but feels instant.

**What is SSE (Server-Sent Events)?**
A one-way stream from server → browser over HTTP. The server keeps the connection open and pushes chunks of data. Browser reads them with `EventSource` or `fetch()` with a stream reader. Simple, works everywhere.

**What is a WebSocket?**
A two-way connection (server ↔ browser). Both sides can send messages anytime. Better for chat because user can send messages while still receiving a stream. Stays connected — no reconnecting per message.

**SSE vs WebSocket — when to use which?**

| | SSE | WebSocket |
|---|---|---|
| Direction | Server → Client only | Both ways |
| Protocol | HTTP (works with proxies) | WS (separate protocol) |
| Reconnection | Built-in auto-reconnect | Manual reconnect logic |
| Use case | Streaming LLM responses | Real-time chat, multiplayer |
| Complexity | Simple | Slightly more setup |

For LLM streaming: SSE is enough. For interactive chat apps: WebSocket is better.

**How does LLM streaming work under the hood?**
```
stream=True in API call
    → Server generates token 1, sends it immediately
    → Server generates token 2, sends it immediately
    → ... repeat until done
    → Server sends [DONE] signal
```
The LLM generates tokens one at a time anyway. Without streaming, the API just buffers them all and sends at the end.

**What changes in the code?**
```python
# Without streaming (module 09):
response = await client.chat.completions.create(model=MODEL, messages=msgs)
answer = response.choices[0].message.content  # Wait for ALL tokens

# With streaming (this module):
stream = await client.chat.completions.create(model=MODEL, messages=msgs, stream=True)
async for chunk in stream:
    token = chunk.choices[0].delta.content  # Get each token as it arrives
    yield token  # Send to browser immediately
```

**What is `delta` vs `message`?**
- `message` = complete response (non-streaming)
- `delta` = incremental piece (streaming). Each chunk has `delta.content` with just the new token(s).

**What is `text/event-stream`?**
The content-type for SSE responses. Browser knows to read it as a stream, not wait for the full body.

**Does streaming use more tokens/cost more?**
No. Same tokens, same cost. The difference is delivery timing only.

**Can I still get the full response for saving to DB?**
Yes — accumulate tokens as you stream them:
```python
full_response = ""
async for chunk in stream:
    token = chunk.choices[0].delta.content or ""
    full_response += token
    yield token
# After loop: full_response has everything
```

**What happens if the connection drops mid-stream?**
SSE: browser auto-reconnects (but loses context). WebSocket: you need manual reconnect logic. In both cases, partial response is lost unless you save server-side.
