# 17 - Observability & Tracing

You can build agents (03, 16), evaluate them (14), and guard them (15). This module
answers a different question: when your agent runs in production and something goes
wrong, **can you see what happened?** Which step failed, how long each took, how many
tokens it burned, and what the model actually saw.

```
print() debugging:   scattered lines, no timing, no grouping, no structure
Observability:       structured spans → one trace per request → metrics you can chart
```

You build the core yourself (a ~40-line tracer) so the concept is concrete, then see
how real tools (OpenTelemetry, Langfuse, LangSmith) are the same idea, industrialized.

## What's in this folder
- `01_why_observability.py` — the pain of debugging an agent with only `print()`
- `02_spans_and_traces.py` — build a tracer: spans (timed steps) nested into a trace
- `03_trace_real_llm.py` — wrap real Groq calls; auto-capture timing + token usage
- `04_structured_logs_and_metrics.py` — JSON logs + roll-ups (p95 latency, error rate, cost)
- `05_real_tools.py` — the production tools and how your code maps onto them

## Run
```bash
cd 17-observability
../.venv/bin/python3 01_why_observability.py
../.venv/bin/python3 02_spans_and_traces.py
../.venv/bin/python3 03_trace_real_llm.py
../.venv/bin/python3 04_structured_logs_and_metrics.py
../.venv/bin/python3 05_real_tools.py
```

Files 01 and 03 make real Groq calls (need `GROQ_API_KEY` in `../.env`).
Files 02, 04, 05 run fully offline.

## Key Q&A

**What's the difference between a log, a metric, and a trace?**
A **log** is one timestamped event ("called get_weather"). A **metric** is a number
tracked over time (latency ms, tokens, error rate). A **trace** is the full story of
ONE request, made of nested **spans** (steps). Logs tell you *what happened*, metrics
tell you *how the system behaves in aggregate*, traces tell you *why one request behaved
the way it did*.

**What is a span?**
A single timed, named unit of work with attributes attached — e.g. `llm.answer`
(0.55s, tokens=88). Spans nest: a parent span (`handle_request`) contains child spans
(`llm.plan`, `tool.get_weather`, `llm.answer`). That tree IS the trace.

**Why isn't `print()` enough?**
Prints have no timing, no token counts, no way to group everything from one request,
and no structure to filter or aggregate. Under concurrent load, prints from different
requests interleave into noise. Structured spans fix all four.

**How do I capture tokens/cost without editing every call?**
Instrument the ONE function that talks to the model (see `traced_chat` in file 03).
Every call routed through it becomes observable automatically. Read `resp.usage` for
`prompt_tokens` / `completion_tokens` / `total_tokens`.

**Why JSON logs instead of pretty text?**
Pretty trees are for reading one request. JSON lines are machine-readable, so a log
platform can index them and let you search ("all spans with status=error") and roll
them up into metrics. That's how you answer "what's my p95 latency this hour?".

**What is p95 latency and why not just use the average?**
p95 = the value 95% of requests are faster than. The average hides the slow tail; a
few very slow requests barely move the average but wreck user experience. p95/p99
surface that tail.

**Which real tool should I use?**
- **OpenTelemetry** — the open standard, vendor-neutral, no lock-in.
- **Langfuse** — LLM-focused, open-source, self-hostable, tracks token cost. Good default.
- **LangSmith** — best if you already use LangChain.
- **Phoenix (Arize)** — strong for debugging RAG/agents with eval views.
All of them use the same span/trace/attribute model you built here.

**How does this connect to evaluation (14) and guardrails (15)?**
Evaluation tells you output *quality*; guardrails *block* bad input/output; observability
tells you *what actually happened and where it broke*. Together they close the loop:
you can measure quality, enforce safety, and debug/operate the system in production.
