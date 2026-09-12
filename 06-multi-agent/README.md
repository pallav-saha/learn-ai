# 06 - Multi-Agent Systems

## What's in this folder
- `01_multi_agent.py` — Content pipeline: Researcher → Writer → Reviewer (linear + iterative)
- `02_multi_agent_patterns.py` — 4 patterns: Parallel, Manager/Worker, Debate, Sub-agents

## Run
```bash
cd 06-multi-agent && ../.venv/bin/python3 01_multi_agent.py
cd 06-multi-agent && ../.venv/bin/python3 02_multi_agent_patterns.py
```

## Key Q&A

**Why multi-agent instead of one agent?**
Each agent has ONE job. Specialized = better results. One agent doing everything loses focus on complex tasks.

**The 4 patterns:**
1. **Parallel** — Multiple agents work simultaneously, results merged
2. **Manager/Worker** — One agent decides which specialist to assign the task to
3. **Debate/Consensus** — Two agents argue opposing sides, a judge decides
4. **Sub-agents as tools** — Main agent delegates to specialized sub-agents

**How do you make different agents?**
Same LLM + different system prompt = different specialist. The system prompt IS the agent's personality.

**What about iterative collaboration?**
Writer writes → Reviewer scores → if score < 8, Writer revises using feedback → Reviewer checks again. Loop until good.

**Key insight:**
All patterns are the same building blocks: Agent class + system prompt + passing outputs between them. The difference is who talks to whom and in what order.
