# Streaming — All Questions & Answers

All the questions asked and answered while learning module 10.

---

## What is streaming?

Instead of waiting 5 seconds for the full answer, the server sends each token (word/piece) as it's generated. The UI renders them immediately. Same total time, but feels instant. Like ChatGPT showing words one by one.

---

## What is SSE (Server-Sent Events)?

A one-way stream from server to browser over normal HTTP. The server keeps the connection open and pushes chunks of data. Simple, works everywhere.

Format is just text:
```
data: Hello\n\n
data:  world\n\n
data: [DONE]\n\n
```

---

## What is a WebSocket?

A persistent two-way connection (server ↔ browser). Both sides can send messages anytime. Better for chat because the user can send messages while still receiving a stream.

---

## SSE vs WebSocket — when to use which?

| | SSE | WebSocket |
|---|---|---|
| Direction | Server → Client only | Both ways |
| Use case | Simple "generate" buttons | Chat interfaces with stop button |
| Reconnection | Built-in auto-reconnect | Manual reconnect logic |
| Complexity | Simple | Slightly more setup |

For LLM streaming: SSE is enough. For interactive chat: WebSocket is better.

---

## What is `stream=True`?

The flag you pass to the LLM API call. Without it, the API buffers all tokens and sends them at the end. With it, the API sends each token as it's generated.

```python
# Without streaming (waits for everything):
response = await client.chat.completions.create(model=MODEL, messages=msgs)
answer = response.choices[0].message.content

# With streaming (gets tokens one by one):
stream = await client.chat.completions.create(model=MODEL, messages=msgs, stream=True)
async for chunk in stream:
    token = chunk.choices[0].delta.content
```

---

## What is `delta` vs `message`?

- `.message` = complete response (non-streaming)
- `.delta` = just the new part, the incremental piece (streaming)

Like a cricket score:
- `.message` = "India 245/3" (final score)
- `.delta` = "+4" (just the latest runs)

---

## Explain `async for chunk in stream` + `yield`

```python
async for chunk in stream:
    content = chunk.choices[0].delta.content
    if content:
        yield content
```

Line by line:
1. **`async for chunk in stream:`** — Wait for the next token from the network. While waiting, free the CPU for others.
2. **`content = chunk.choices[0].delta.content`** — Extract the text piece from the chunk object.
3. **`if content:`** — Skip chunks with no text (first chunk has role info, last chunk has finish signal).
4. **`yield content`** — Hand this one token to the caller immediately. Don't wait for more.

---

## What is `yield` vs `return`?

- `return` = collect everything, give ALL at once. Like downloading a full movie then watching.
- `yield` = give each piece as it arrives. Like streaming a movie — watch while downloading.

`yield` pauses the function and resumes it when the next value is requested.

---

## Does YouTube also stream this way?

Same core idea (deliver pieces instead of waiting for everything), but different:

| | LLM Streaming | YouTube Streaming |
|---|---|---|
| Data | Text tokens (~4 bytes) | Video chunks (~1-5MB) |
| Content | Being generated in real-time | Already exists on server |
| Seek/skip | Can't jump ahead (not generated yet) | Can jump anywhere |
| Protocol | SSE or WebSocket | HLS or DASH |

YouTube = delivering pre-made content in chunks.
LLM streaming = delivering content as it's being CREATED.

---

## Why does `async` appear in 3 places?

```python
async def stream_tokens():              # ← async #1
    async for chunk in get_chunks():    # ← async #2
        yield chunk

async for token in stream_tokens():    # ← async #3
    print(token)
```

1. **`async def`** — "This function has network waits inside." Required to use `await` or `async for` inside.
2. **`async for chunk in get_chunks()`** — "The source delivers items with network waits. Between items, free up the CPU." Required because `get_chunks()` is async.
3. **`async for token in stream_tokens()`** — "The source (stream_tokens) is async, so I must use async for to consume it."

**The chain rule:** If ANYTHING in the chain waits on the network, EVERYTHING above it becomes async. It's contagious — propagates upward.

---

## Normal `for` vs `async for`

| | `for` + `yield` | `async for` + `yield` |
|---|---|---|
| During wait | Entire program freezes | CPU freed for other tasks |
| Use when | Single-user scripts | Web servers with multiple users |
| Analogy | One cashier, everyone waits | Cashier helps others while your card processes |

---

## What if you remove one `async`?

- Remove `async def` → SyntaxError (can't use `await` in normal function)
- Use normal `for` on async generator → TypeError ("async_generator is not iterable")

Async producers need async consumers. Like plugging a US charger into a UK outlet — the shapes don't match.

---

## Does streaming cost more tokens?

No. Same tokens, same cost. The difference is delivery timing only.

---

## Can I still save the full response while streaming?

Yes — accumulate tokens as you stream:
```python
full_response = ""
async for chunk in stream:
    token = chunk.choices[0].delta.content or ""
    full_response += token
    yield token
# After loop: full_response has everything
```

---

## What happens if the connection drops mid-stream?

- SSE: browser auto-reconnects (but loses context of partial response)
- WebSocket: you need manual reconnect logic
- In both cases: partial response is lost unless saved server-side

---

## What is `return` vs `yield`?

- `return` = collect everything, give ALL at once. Function runs to completion, then returns.
- `yield` = give each piece as it arrives. Function pauses at each yield, resumes when next value is requested.

Analogy:
- `return` = downloading a full movie, then watching
- `yield` = streaming a movie (watch while downloading)

---

## Normal `for` + `yield` vs `async for` + `yield`?

| | `for` + `yield` | `async for` + `yield` |
|---|---|---|
| During wait | Entire program freezes | CPU freed for other tasks |
| Use when | Single-user scripts | Web servers with multiple users |
| Analogy | One cashier, everyone waits | Cashier helps others while your card processes |

---

## Why does `async` appear in 3 places?

```python
async def stream_tokens():              # async #1
    async for chunk in get_chunks():    # async #2
        yield chunk

async for token in stream_tokens():    # async #3
    print(token)
```

1. **`async def`** — "This function has network waits inside." Required to use `await` or `async for` inside.
2. **`async for chunk in get_chunks()`** — "The source delivers items with network waits. Between items, free the CPU." Required because `get_chunks()` is an async generator.
3. **`async for token in stream_tokens()`** — "The source is async, so I must use async for to consume it."

The chain rule: if ANYTHING in the chain waits on the network, EVERYTHING above it becomes async. It's contagious.

---

## When to use `await` alone vs `async for` + `yield`?

| Situation | Use | Analogy |
|---|---|---|
| One result, wait for it | `await` | Order food delivery — wait, get full meal |
| Many results over time | `async for` + `yield` | Live score — updates arrive one by one |

```python
# await alone: one complete result
response = await client.create(stream=False)
answer = response.choices[0].message.content  # Full answer at once

# async for: many pieces over time
stream = await client.create(stream=True)
async for chunk in stream:
    token = chunk.choices[0].delta.content  # One piece at a time
```

Short version:
- `await` = "give me the whole pizza when it's done"
- `async for` + `yield` = "give me each slice as it comes out of the oven"

---

## What does `*[handle_request(i+1) for i in range(5)]` mean?

Two things happening:

1. **List comprehension** `[handle_request(i+1) for i in range(5)]` — creates a list of 5 function calls:
```python
[handle_request(1), handle_request(2), handle_request(3), handle_request(4), handle_request(5)]
```

2. **`*` (unpacking)** — removes the brackets and passes them as separate arguments:
```python
# These are identical:
await asyncio.gather(*my_list)
await asyncio.gather(handle_request(1), handle_request(2), handle_request(3), handle_request(4), handle_request(5))
```

`asyncio.gather()` expects separate arguments, not a list. `*` unpacks the list into separate arguments.

---

## Why `\n\n` in SSE streaming?

That's the SSE protocol rule. Every SSE message MUST end with two newlines (`\n\n`). That's how the browser knows "this message is complete."

```
data: Hello\n\n      ← Browser: "Message 1 is 'Hello'"
data:  world\n\n     ← Browser: "Message 2 is ' world'"
```

The double newline is the separator — like a period at the end of a sentence. Without it, the browser doesn't know where one event ends and the next begins.

---

## Why `[DONE]` and is it a list?

NOT a Python list. Just a string with brackets. It's a convention (invented by OpenAI) meaning "stream is over, no more tokens coming."

The brackets make it visually distinct from actual content — you'd never write `[DONE]` in a real sentence.

On the browser side:
```javascript
if (token === '[DONE]') break;  // Stop reading
```

You could use any signal (`"END"`, `"STOP"`) but `[DONE]` is the standard everyone follows.
