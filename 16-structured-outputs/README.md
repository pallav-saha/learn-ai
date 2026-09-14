# 16 - Structured Outputs & Function Calling

In module 03 you gave an agent tools using hand-parsed text. This module shows the
MODERN, production way: get the LLM to return reliable structured data (JSON that
matches a schema) and to call functions with validated arguments.

```
Free text output:     "The user's name is Alice and she is 30 years old."   (hard to use)
Structured output:    {"name": "Alice", "age": 30}                          (ready to use)
```

## What's in this folder
- `01_json_mode.py` — get JSON back instead of free text (`response_format`)
- `02_pydantic_schemas.py` — define a schema with Pydantic, validate the LLM's JSON
- `03_function_calling.py` — the LLM picks a tool and returns structured arguments
- `04_agent_with_tools.py` — a full agent loop: think → call tool → observe → repeat

## Run
```bash
cd 16-structured-outputs
../.venv/bin/python3 01_json_mode.py
../.venv/bin/python3 02_pydantic_schemas.py
../.venv/bin/python3 03_function_calling.py
../.venv/bin/python3 04_agent_with_tools.py
```

## Key Q&A

**Why do I need structured output? Can't I just parse the text?**
Free-text answers are unpredictable — "Alice, 30" vs "Her name is Alice, age 30" vs
"The person is 30 and called Alice." Parsing that with string code is fragile and breaks
constantly. Structured output makes the LLM return clean JSON your code can use directly.

**What is JSON mode?**
Passing `response_format={"type": "json_object"}` forces the model to output valid JSON
(not prose). You still have to describe the shape you want in the prompt, but you're
guaranteed parseable JSON back. You saw this already in modules 14/15 for the judges.

**What is a Pydantic schema and why use it?**
Pydantic lets you define the exact shape of your data as a Python class (fields + types).
You then validate the LLM's JSON against it — if the model returns a wrong type or misses
a field, you catch it immediately instead of crashing later. It's a contract for the data.

**What is function calling (a.k.a. tool calling)?**
You describe your functions (name + parameters as a schema) to the LLM. Instead of
answering in text, the LLM can respond "call `get_weather` with `{city: 'Tokyo'}`". Your
code runs the real function and feeds the result back. The LLM decides WHICH tool and
WHAT arguments — reliably, as structured data.

**How is this different from module 03's agent?**
Module 03 parsed the LLM's text to guess which tool it wanted (fragile). Function calling
is built into the API: the model returns a structured `tool_calls` object with the function
name and validated JSON arguments. No text parsing, far more reliable.

**What's the function-calling loop?**
1. Send the user message + your tool definitions
2. LLM responds with a tool call (name + arguments) OR a final answer
3. If a tool call: run the real function, append the result, go back to step 1
4. If a final answer: done
This loop (think → act → observe → repeat) is the heart of every AI agent.

**Structured output vs function calling — when to use which?**
- **Structured output**: you want the LLM's ANSWER in a specific shape (extract fields,
  classify, return a form). One call, get structured data back.
- **Function calling**: you want the LLM to DO something (fetch data, take an action) by
  calling your code. Multi-step, the LLM drives which tools run.

**Does every model support this?**
Most major models (OpenAI, Groq's larger models, Anthropic) support function calling and
JSON mode. Smaller/older models may not, or may be unreliable. This module uses Groq's
gpt-oss-20b, which supports both.

**What if the model returns invalid JSON or bad arguments?**
JSON mode makes invalid JSON rare, but validate anyway (Pydantic). For function calling,
validate the arguments before running the function — never trust the LLM's args blindly
(same principle as the guardrails module: treat model output as untrusted).
