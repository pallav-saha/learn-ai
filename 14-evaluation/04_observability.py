"""
04 - Observability

Evaluation = "is the output good?" (offline testing on a dataset)
Observability = "what's happening in production?" (logging every real call)

This builds a simple TRACER that records every LLM call:
  - latency (how long it took)
  - tokens (input/output)
  - cost (in dollars)
  - success/error
  - the full "trace" of a multi-step flow

Production tools (Langfuse, LangSmith, Helicone) do this at scale with dashboards.
Here we build it by hand so you understand what they do under the hood.

Run:
    cd 14-evaluation && ../.venv/bin/python3 04_observability.py
"""

import os
import time
import json
import uuid
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

# Approx Groq pricing for cost tracking
PRICE_INPUT = 0.10 / 1_000_000
PRICE_OUTPUT = 0.50 / 1_000_000


# ============================================================
# THE TRACER — records everything about each call
# ============================================================

class Tracer:
    """
    Collects observability data. In production this would push to Langfuse/a database.
    Here we keep it in a list and print a summary.
    """
    def __init__(self):
        self.spans = []  # each "span" = one recorded operation (an LLM call, a step, etc.)

    def record(self, span: dict):
        self.spans.append(span)

    @contextmanager
    def trace_llm(self, name: str, trace_id: str = None):
        """
        Context manager that times an LLM call and records it.

        Usage:
            with tracer.trace_llm("answer_question") as span:
                response = client.chat.completions.create(...)
                span["response"] = response   # let the tracer read tokens/cost
        """
        span = {
            "name": name,
            "trace_id": trace_id or str(uuid.uuid4())[:8],
            "start": datetime.now().isoformat(),
            "response": None,
            "error": None,
        }
        start = time.time()
        try:
            yield span  # the caller runs the LLM call and sets span["response"]
        except Exception as e:
            span["error"] = str(e)
            raise
        finally:
            span["latency_s"] = round(time.time() - start, 3)

            # Extract tokens + cost from the response (if set)
            resp = span.pop("response", None)
            if resp is not None:
                usage = resp.usage
                span["input_tokens"] = usage.prompt_tokens
                span["output_tokens"] = usage.completion_tokens
                span["cost_usd"] = round(
                    usage.prompt_tokens * PRICE_INPUT + usage.completion_tokens * PRICE_OUTPUT, 8
                )
            self.record(span)

    def summary(self):
        """Print an observability report — what production dashboards show."""
        print("\n  " + "=" * 56)
        print("  OBSERVABILITY REPORT")
        print("  " + "=" * 56)
        total_cost = 0.0
        total_latency = 0.0
        errors = 0
        for s in self.spans:
            status = "ERROR" if s.get("error") else "OK"
            cost = s.get("cost_usd", 0)
            total_cost += cost
            total_latency += s.get("latency_s", 0)
            if s.get("error"):
                errors += 1
            print(f"    [{status}] {s['name']:22s} | "
                  f"{s.get('latency_s', 0):.2f}s | "
                  f"{s.get('input_tokens', 0)}+{s.get('output_tokens', 0)} tok | "
                  f"${cost:.6f}")
        print("  " + "-" * 56)
        print(f"    Total calls:   {len(self.spans)}")
        print(f"    Total cost:    ${total_cost:.6f}")
        print(f"    Total latency: {total_latency:.2f}s")
        print(f"    Errors:        {errors}")


# global tracer
tracer = Tracer()


# ============================================================
# DEMO 1: trace individual calls
# ============================================================

def demo_single_calls():
    print("=" * 60)
    print("  [1] Tracing individual LLM calls")
    print("=" * 60)

    questions = [
        "What is Python?",
        "What is a REST API?",
        "Explain recursion in one sentence.",
    ]

    for q in questions:
        with tracer.trace_llm(name="qa_call") as span:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": q}],
                temperature=0.5,
                max_tokens=100,
            )
            span["response"] = response  # give the tracer the response to extract metrics
        print(f"    Traced: '{q}'")


# ============================================================
# DEMO 2: trace a multi-step flow (one trace_id links the steps)
# ============================================================

def demo_multi_step_trace():
    print("\n" + "=" * 60)
    print("  [2] Tracing a multi-step flow (one request, several LLM calls)")
    print("=" * 60)

    # One trace_id ties all steps of a single user request together.
    trace_id = str(uuid.uuid4())[:8]
    print(f"    Trace ID: {trace_id} (links all steps below)")

    topic = "the water cycle"

    # Step 1: generate an outline
    with tracer.trace_llm(name="step1_outline", trace_id=trace_id) as span:
        r1 = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Give a 3-point outline about {topic}."}],
            temperature=0.5, max_tokens=120,
        )
        span["response"] = r1
    outline = r1.choices[0].message.content

    # Step 2: expand the outline (depends on step 1's output)
    with tracer.trace_llm(name="step2_expand", trace_id=trace_id) as span:
        r2 = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Write one paragraph based on this outline:\n{outline}"}],
            temperature=0.5, max_tokens=150,
        )
        span["response"] = r2

    print("    Traced a 2-step flow (outline → expand) under one trace_id.")
    print("    In a dashboard, you'd see both steps grouped under this request.")


# ============================================================
# DEMO 3: save traces to a file (like sending to a backend)
# ============================================================

def save_traces():
    out_path = os.path.join(os.path.dirname(__file__), "traces.json")
    with open(out_path, "w") as f:
        json.dump(tracer.spans, f, indent=2)
    print(f"\n  Saved {len(tracer.spans)} traces to traces.json")
    print("  (In production, these would stream to Langfuse/a database in real time.)")


def main():
    demo_single_calls()
    demo_multi_step_trace()
    tracer.summary()
    save_traces()

    print("\n  " + "=" * 56)
    print("  Evaluation vs Observability:")
    print("    Evaluation    = 'is the output good?' (offline, on a test set)")
    print("    Observability = 'what happened live?' (logging real calls)")
    print("  You need BOTH: eval catches regressions before deploy,")
    print("  observability catches real-world issues after deploy.")


if __name__ == "__main__":
    main()
