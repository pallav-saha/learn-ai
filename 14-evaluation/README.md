# 14 - Evaluation & Observability

You've learned to BUILD and SCALE LLM apps. Now learn to answer the question every
team asks after "does it run?" → **"Is it actually any good?"**

## What's in this folder
- `01_llm_as_judge.py` — grade answers automatically using an LLM as the judge
- `02_rag_evaluation.py` — measure RAG quality: faithfulness, relevance, context precision
- `03_eval_dataset.py` — build a test set and run evaluation across it (like unit tests for LLMs)
- `04_observability.py` — trace/log every LLM call: cost, latency, tokens, errors

## Run
```bash
cd 14-evaluation
../.venv/bin/python3 01_llm_as_judge.py
../.venv/bin/python3 02_rag_evaluation.py
../.venv/bin/python3 03_eval_dataset.py
../.venv/bin/python3 04_observability.py
```

## Key Q&A

**Why can't I just eyeball the outputs?**
You can for 5 examples. But with hundreds of test cases, or when you change a prompt and
need to know "did this make things better or worse?", you need automated, repeatable
measurement. Eyeballing doesn't scale and isn't objective.

**What is "LLM-as-judge"?**
Use a second LLM to GRADE the output of your main LLM. Instead of a human reading every
answer, you ask an LLM "is this answer correct/relevant/faithful? Score 1-5 and explain."
It's cheap, fast, and surprisingly good — the standard technique for LLM evaluation.

**Isn't it circular to use an LLM to grade an LLM?**
It feels that way, but grading is EASIER than generating. Judging "does this answer match
the reference?" is a simpler task than producing the answer from scratch. Research shows
LLM judges correlate well with human ratings. You reduce risk by: using a strong judge
model, giving clear scoring criteria, and spot-checking the judge against human labels.

**What are the key RAG metrics?**
- **Faithfulness**: is the answer grounded in the retrieved context, or did it hallucinate?
- **Answer relevance**: does the answer actually address the question?
- **Context precision/recall**: did retrieval fetch the RIGHT chunks?

These separate "retrieval is broken" from "generation is broken" — crucial for debugging RAG.

**What is an eval dataset?**
A fixed set of test cases (question + expected answer, or question + reference context).
You run your system against ALL of them and get a score. Like unit tests, but for LLM
quality. When you change a prompt/model, re-run the eval to see if the score went up or down.

**What is observability (vs evaluation)?**
- **Evaluation** = "is the output good?" (quality — measured on a test set)
- **Observability** = "what happened in production?" (logging every real call: latency,
  cost, tokens, errors, the full trace of a multi-step flow)

Evaluation is offline testing. Observability is watching the live system.

**What is a "trace"?**
A record of everything that happened for one request — every LLM call, tool call, retrieval,
with timing and cost. For a multi-step agent, the trace shows the full chain so you can see
where it went wrong or got slow.

**What tools do this in production?**
- **Langfuse** (open-source, free, self-hostable) — traces, evals, cost tracking
- **LangSmith** (by LangChain) — similar, hosted
- **Phoenix/Arize**, **Helicone** — observability
- **RAGAS**, **DeepEval** — evaluation frameworks
This module builds the concepts by hand so you understand what these tools do under the hood.

**Offline eval vs online eval?**
- **Offline**: run your eval dataset before shipping (like tests in CI)
- **Online**: sample real production traffic and grade it (catches issues eyeballing misses)
Do both: offline to catch regressions before deploy, online to monitor real quality.
