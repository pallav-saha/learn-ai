# Async & Await in Python — Complete Notes

---

## What Problem Does Async Solve?

Most server work is **waiting** — waiting for a database, waiting for an API, waiting for a file to load. During that wait, a synchronous server does **nothing**. Async lets the server handle other requests during that idle time.

---

## The Core Concept

```
Sync  = Do one thing. Wait. Do next thing. Wait. (like standing at the door waiting for Zomato)
Async = Start something. While waiting, do other stuff. Come back when it's ready. (order food, watch TV, grab it when doorbell rings)
```

---

## The One Rule to Remember

**Ask: "Does this function LEAVE my computer to do its work?"**

| Answer | What to do | Examples |
|--------|-----------|----------|
| YES — goes over network/disk | Use `await` | Database queries, API calls, file I/O, email sending |
| NO — works in memory | No `await` needed | Math, string manipulation, sorting, filtering lists |

---

## Visual: How Async Handles Multiple Users

### Sync (Flask) — One at a time:

```
User A: [request] → [wait for DB ⏳⏳⏳⏳⏳] → [respond]
User B:                                          [request] → [wait ⏳⏳⏳⏳⏳] → [respond]
User C:                                                                           [request] → ...
```

Total time for 3 users: 15 seconds (5+5+5, sequential)

### Async (FastAPI) — Concurrent:

```
User A: [request] → [wait for DB ⏳⏳⏳⏳⏳] → [respond]
User B: [request] → [wait for DB ⏳⏳⏳⏳⏳] → [respond]
User C: [request] → [wait for DB ⏳⏳⏳⏳⏳] → [respond]
```

Total time for 3 users: 5 seconds (all 3 run during same wait period)

---

## Code Comparison

### Without async (Flask):

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    result = call_groq_api(data["message"])  # BLOCKS — server frozen here
    return jsonify({"reply": result})
```

### With async (FastAPI):

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/chat")
async def chat(data: dict):
    result = await call_groq_api(data["message"])  # FREES UP — handles others while waiting
    return {"reply": result}
```

---

## Multi-Step Example: When to Use await

Scenario: Upload CSV → validate → transform → save to DB → notify API → return

```python
@app.post("/upload")
async def upload_csv(file):
    # Step 1: Validate — NO await (checking data in memory)
    errors = validate_csv(file)

    # Step 2: Transform — NO await (CPU work, looping through rows)
    rows = transform_rows(file)

    # Step 3: Save to DB — YES await (sending data to database server)
    await db.insert_many(rows)

    # Step 4: Call external API — YES await (going over the internet)
    await httpx.post("https://api.example.com/notify", json={"count": len(rows)})

    # Step 5: Build response — NO await (just creating a dict)
    summary = {"rows_processed": len(rows), "errors": len(errors)}

    # Step 6: Send email — YES await (connecting to email server)
    await email.send(to="user@email.com", body=str(summary))

    return summary
```

### Decision Table:

| Function | await? | Reason |
|----------|--------|--------|
| `validate_csv(file)` | No | Just checking data in RAM |
| `transform_rows(file)` | No | CPU work — looping, modifying data |
| `db.insert_many(rows)` | Yes | Goes to database server over network |
| `httpx.post(...)` | Yes | Goes to external API over internet |
| `generate_summary()` | No | Building a dictionary in memory |
| `email.send(...)` | Yes | Goes to email server over network |

---

## Quick Reference: Common Operations

### These DON'T need await (in-memory, instant):

```python
total = sum(prices)
filtered = [x for x in items if x > 10]
user_dict = {"name": name, "age": age}
json_string = json.dumps(data)
cleaned = text.strip().lower()
sorted_list = sorted(items, key=lambda x: x.name)
result = 15 * 4 + 37
```

### These NEED await (leave your computer):

```python
user = await db.get_user(id=5)                    # Database
weather = await httpx.get("https://api.weather")  # External API
result = await groq_client.chat(...)              # LLM API
file_data = await aiofiles.open("large.csv")      # Disk I/O
await cache.set("key", value)                     # Redis/cache server
await email.send(to="x@y.com", body="hi")         # Email server
await s3.upload(file)                             # Cloud storage
```

---

## What If CPU Work Is Slow?

If a transform takes seconds (large file processing), it blocks even in async. Solution:

```python
import asyncio

async def process():
    # Moves heavy CPU work to a thread so it doesn't block other requests
    data = await asyncio.to_thread(heavy_transform, file)
    await db.save(data)
```

---

## The "Unplug Test"

If you unplug your internet or shut down your database, would the function break?

- **Yes** → it needs `await` (it depends on something external)
- **No** → it doesn't need `await` (it works purely in memory)

---

## Key Terms

| Term | Meaning |
|------|---------|
| `async` | Marks a function as capable of using `await` |
| `await` | "Start this, go do other stuff, come back when done" |
| I/O-bound | Work that spends most time waiting (network, disk) |
| CPU-bound | Work that spends most time computing (math, loops) |
| Concurrent | Multiple tasks in progress at the same time |
| Blocking | Code that freezes everything until it finishes |

---

## When to Use What

| Scenario | Recommendation |
|----------|---------------|
| Building a web API | Always use async (FastAPI) |
| Script that runs once | Sync is fine (no need for async) |
| Multiple API calls needed | `await` each one, or `asyncio.gather()` for parallel |
| Heavy computation | `asyncio.to_thread()` or multiprocessing |
| Learning / prototyping | Whatever's simpler — don't overthink it |

---

## Flask vs FastAPI Summary

| | Flask | FastAPI |
|---|---|---|
| Style | Sync (blocking) | Async (non-blocking) |
| Performance | 1 request at a time per worker | Thousands concurrent |
| Validation | Manual (write if/else checks) | Automatic (type hints) |
| API Docs | None | Free at /docs |
| Best for | Simple apps, learning | Production APIs |
| Released | 2010 | 2018 |

---

## One-Line Summary

> **`await` = "this goes over the network, don't freeze while waiting."**
