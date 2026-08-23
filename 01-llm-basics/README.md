# 01 - LLM Basics

## What's in this folder
- `llm_basics.py` — Your first LLM API call (prompt → completion flow)

## Run
```bash
cd 01-llm-basics && ../.venv/bin/python3 llm_basics.py
```

## Key Q&A

**What is an LLM?**
A program trained on massive text that predicts "what comes next." It doesn't "know" things — it generates the most likely text based on patterns.

**What are tokens?**
Chunks of text the model reads. "Hello world" = 2 tokens. Models have a context window (max tokens they can see at once).

**What is temperature?**
Controls randomness: 0.0 = same answer every time, 1.0 = creative/varied, 2.0 = chaotic.

**What does the model actually do?**
`[Your prompt] → [pattern matching on billions of texts] → [generated response]`

**Is Llama free?**
Llama is just model weights from Meta. Use it free via Groq, OpenRouter, or Ollama (local).

**What's the difference between models (20B vs 120B)?**
More parameters = better at complex tasks but slower. 20B is fast, 120B is smarter.
