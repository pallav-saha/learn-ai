# AI Fundamentals — Key Questions & Answers

A collection of important questions from the learning session, organized by topic.

---

## LLMs (Large Language Models)

### What is an LLM?
A program trained on massive text data that predicts "what comes next." It doesn't "know" things — it generates the most likely text based on patterns. Think of it as autocomplete on steroids.

### Is Llama free? Does it have an API key?
Llama is just model weights released by Meta — no API included. But you can use it free through:
- **Groq** (console.groq.com) — free, fast, no credit card
- **Together AI** — $5 free credits
- **Ollama** (local) — runs on your machine, unlimited

### What's the latest in AI?
Agentic AI is the current wave — LLMs given the ability to take action, not just talk. The progression: LLMs → AI Assistants → AI Agents.

---

## Free Models & Providers

### What is OpenRouter?
A middleman/router. You sign up once, get one API key, and access 200+ models from all providers (OpenAI, Google, Meta, Mistral) through a single endpoint. Like Uber Eats for AI models.

### What's the best free model?
Depends on what you need:
- **Most models, one key** → OpenRouter
- **Best single model quality** → Google AI Studio (Gemini 2.5 Flash)
- **Fastest speed** → Groq (1000 tokens/sec)
- **No limits ever** → Ollama (runs locally)

### Is `openai/gpt-oss-20b` free?
Yes, on Groq's developer plan. 250K tokens/min, no credit card needed. The "oss" stands for "open source" — it's not GPT-4.

### What does "Local/Offline" mean? Do I need to download?
Yes — you download the model (~5-40GB depending on size) to your Mac via Ollama. It runs entirely on your machine. No internet, no API key, no limits, no cost after download.

---

## Python Environment

### What's the latest way to create a venv?
`uv` is the modern tool (2024+). Fast, replaces pip + virtualenv + pyenv in one tool.
```bash
uv venv          # create
uv pip install   # install packages
```

### Why didn't `make setup` activate the venv?
`source .venv/bin/activate` only affects the shell it runs in. Each Makefile command runs in its own subshell that dies after the line finishes. No script can activate a venv in your parent shell. Workaround: use `.venv/bin/python3` directly.

---

## Agents

### What makes an agent different from a chatbot?
A chatbot answers. An agent **acts**. It has tools, a planning loop, and decides autonomously which steps to take.

### What is the `tools` JSON schema for?
It's a menu you hand to the LLM describing what functions are available. The LLM reads the `description` fields to decide when to use each tool. It can't see your Python code directly — only the schema.

### When does the agent use multiple steps?
When one tool call isn't enough — either multiple independent tools are needed, or the output of one tool feeds into another.

### What if the question doesn't match any tool?
With `tool_choice="auto"`, the LLM just answers directly from its knowledge. No tool is called.

---

## Flask vs FastAPI

### Which is better?
FastAPI is the modern choice for APIs (2018+). Flask is simpler but older (2010).
- FastAPI: async, auto-validation, free docs at `/docs`
- Flask: sync, manual validation, no auto docs

### What is `request.get_json()`?
Flask reads the raw HTTP request body (bytes), parses the JSON string, and returns a Python dictionary.

---

## Async / Await

### What does "frees up while waiting" mean?
When your code calls an external service (API, database), it's just waiting for a response. `await` tells Python: "go handle other requests while I wait." Without it, the server is frozen doing nothing.

### When to use `await`:
**Ask: "Does this function leave my computer to do its work?"**
- YES (network, database, file I/O) → use `await`
- NO (math, string manipulation, sorting) → no `await`

### Does the transform step (CPU work) block other requests?
Yes! Only `await`-ed operations free up for other requests. Pure CPU work blocks. If CPU work is slow, wrap it in `asyncio.to_thread()`.

### Should I always use async?
For web APIs — yes. For scripts that run once — sync is fine. For heavy computation — use multiprocessing, not async.

---

## RAG (Retrieval Augmented Generation)

### Why is it called RAG?
It's just 3 words:
- **Retrieval** — search your documents
- **Augmented** — paste relevant parts into the prompt
- **Generation** — LLM generates an answer from that context

The concept is simple: look up relevant info, add it to the prompt, let the LLM answer. Researchers gave it a fancy name but it's literally "search before answering."

### What is chunking and why?
Splitting documents into small pieces so you can search and send only the relevant part to the LLM — not the entire document. Saves tokens and improves accuracy.

### How to choose chunk size?
- How long is one "complete thought" in your docs?
- What's your embedding model's max input? (must be smaller)
- Start with 500-1000 chars for real documents. Adjust based on answer quality.

---

## Embeddings

### What is an embedding?
Converting text into a list of numbers (vector) that represents its **meaning**. Similar texts → similar numbers → close in vector space.

### How does text become numbers?
1. **Tokenize** — break sentence into sub-word pieces
2. **Lookup** — each token gets an initial number vector (from training)
3. **Process** — transformer layers adjust numbers based on context/relationships
4. **Average** — all token vectors merge into one sentence vector

### Why embeddings instead of keyword search?
Keywords fail when different words mean the same thing:
- "vacation days" won't match "paid time off"
- "Can I get my money back?" won't match "refund policy"

Embeddings catch these because they search by meaning, not exact words.

### Why 256 tokens ≈ 512 characters?
Rough estimate: 1 token ≈ 2 characters on average in English. Not exact — varies by text. Used for planning chunk sizes.

### Where does the embedding model get downloaded?
`~/.cache/huggingface/` — shared across all projects. Downloaded once, cached forever. Not in `.venv` because you'd re-download every time you recreate the environment.

### What happens if a chunk exceeds the model's max input tokens?
The model **silently truncates** — it only processes the first 256 tokens and ignores everything after that. No error, no warning. The embedding will only represent the beginning of the chunk, and information at the end is lost. This is why chunk size must be smaller than the model's max input.

```
Chunk: "Sentence 1. Sentence 2. Sentence 3. Sentence 4. Sentence 5. Sentence 6."
                                         ↑ 256 tokens (model stops here)
Model sees:  "Sentence 1. Sentence 2. Sentence 3. Sentence 4."
Model ignores: "Sentence 5. Sentence 6."  ← LOST, not embedded
```

**Safe limits:**
- all-MiniLM-L6-v2: max 256 tokens → keep chunks under ~500 chars
- OpenAI text-embedding-3-small: max 8191 tokens → chunks can be up to ~15,000 chars

### Which line downloads the model?
```python
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
```
This single line checks cache, downloads if missing, and loads into memory.

### Why not use OpenAI for embeddings?
OpenAI embeddings are paid only (no free tier). The local model (all-MiniLM-L6-v2) is free, instant, works offline, and keeps your data private.

---

## Tools & Setup

### What is `user_agent` in Wikipedia API?
Just a name tag identifying who's making the request. Free, no verification. Wikipedia requires it so they can contact you if your script sends too many requests.

### What does the `@retry_on_failure` decorator do?
Automatically retries a function if it fails. Waits longer between each retry (exponential backoff: 1s → 2s → 4s). Gives up after 3 attempts.

---

## What I Learned (Summary)

| # | Topic | Key Takeaway |
|---|-------|-------------|
| 1 | LLMs | Text in → text out. Predicts, doesn't "know." |
| 2 | Prompt Engineering | Better prompts → better outputs. Use role + context + format. |
| 3 | AI Agents | LLM + tools + loop = agent. It decides when/how to use tools. |
| 4 | Flask/FastAPI | FastAPI is modern. Async for APIs, sync for scripts. |
| 5 | Async/Await | `await` = "this goes over the network, don't freeze." |
| 6 | RAG | Search docs, paste in prompt, LLM answers from your data. |
| 7 | Embeddings | Text → numbers by meaning. Similar text → close numbers. |

---

## What's Next

- Multi-agent systems (multiple agents collaborating)
- Vector databases (storing embeddings at scale — Pinecone, ChromaDB)
- Memory & conversations (long-term agent memory)
- Deploying AI apps (Docker, cloud, making it live)
- LangChain / CrewAI (production agent frameworks)
