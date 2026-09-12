# 02 - Prompt Engineering

## What's in this folder
- `01_prompt_engineering.py` — 6 techniques demonstrated with bad vs good prompts

## Run
```bash
cd 02-prompt-engineering && ../.venv/bin/python3 01_prompt_engineering.py
```

## Key Q&A

**What is prompt engineering?**
Writing inputs that get better outputs from LLMs. Same model, better prompt = drastically better answers.

**The 6 techniques:**
1. **Be Specific** — "Tell me about Python" vs "Explain list comprehensions in 3 sentences"
2. **Role Prompting** — "You are a senior Python developer..."
3. **Few-Shot Examples** — Show 3 examples, model continues the pattern
4. **Chain of Thought** — "Think step by step" improves reasoning/math
5. **Output Format** — Tell it exactly what format (JSON, bullets, code)
6. **Constraints** — "Max 3 bullets, 15 words each, no jargon"

**The formula:**
`[Role] + [Context] + [Specific Task] + [Output Format] + [Constraints]`

**Key insight:**
You don't need a better model — you need a better prompt.
