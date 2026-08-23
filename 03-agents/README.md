# 03 - AI Agents

## What's in this folder
- `agent_basics.py` — An agent with tools (calculator, time, dictionary, Wikipedia)

## Run
```bash
cd 03-agents && ../.venv/bin/python3 agent_basics.py
```

## Key Q&A

**What makes an agent different from a chatbot?**
A chatbot answers. An agent ACTS. It has tools, a planning loop, and decides autonomously which steps to take.

**What is the agent loop?**
```
THINK → ACT → OBSERVE → repeat until done
```
Same pattern as every AI coding assistant (Kiro, Cursor, etc.)

**What is the `tools` JSON schema?**
A menu you hand to the LLM describing what functions are available. The LLM reads descriptions to decide when to use each tool.

**What if the question doesn't match any tool?**
With `tool_choice="auto"`, the LLM just answers directly from its knowledge. No tool is called.

**When does the agent use multiple steps?**
When one tool call isn't enough — either multiple tools needed, or output of one feeds into another.

**Key insight:**
Every AI product is just: LLM + tools + a loop. The tools are the power. The LLM is the brain that decides when/how to use them.
