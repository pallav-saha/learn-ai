# 08 - Memory & Conversations

## What's in this folder
- `memory_1_short_term.py` — Just a messages list (forgets on exit)
- `memory_2_long_term.py` — Saves to JSON file (remembers across runs)
- `memory_3_semantic.py` — ChromaDB for searchable past conversations
- `memory_agent.py` — All 3 combined into one agent

## Run (step by step)
```bash
cd 08-memory && ../.venv/bin/python3 memory_1_short_term.py
cd 08-memory && ../.venv/bin/python3 memory_2_long_term.py
cd 08-memory && ../.venv/bin/python3 memory_3_semantic.py
```

## Key Q&A

**Do LLMs have memory?**
No. Every API call is a fresh start. Memory is built by the code AROUND the LLM.

**How does ChatGPT "remember"?**
Sends the ENTIRE conversation history with every request. The model re-reads all previous messages.

**The 3 types:**
1. **Short-term** — `messages` list in RAM. Grows each turn. Gone on exit.
2. **Long-term** — Save facts to a file (JSON). Survives restarts.
3. **Semantic** — Store conversations in ChromaDB. Searchable by meaning.

**Why keep last 10 messages if ChromaDB has everything?**
The LLM needs structured messages (role + content) for conversation flow. ChromaDB stores raw text blobs for search — different purpose. Last 10 = active awareness. ChromaDB = long-term recall.

**New session with existing ChromaDB — what happens?**
System prompt + your message + relevant ChromaDB results injected. The LLM sees past context even with empty messages list.

**How do ChatGPT/Perplexity store memory for millions of users?**
Same pattern, cloud database indexed by user_id. Your lookup takes ~1ms regardless of total users (indexed query).
