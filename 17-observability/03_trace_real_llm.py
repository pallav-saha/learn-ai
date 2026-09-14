"""
03 - Tracing a REAL agent + capturing token usage automatically

Now we point the tracer from file 02 at real Groq calls. The key upgrade:
a helper `traced_chat()` that wraps every LLM call so it AUTOMATICALLY records:
    - duration (how slow)
    - model name
    - prompt / completion / total tokens (how expensive)
    - an error, if the call throws

This is the pattern real tools use: instrument the ONE function that talks to the
model, and every call in your whole app becomes observable for free.

Run:
    cd 17-observability && ../.venv/bin/python3 03_trace_real_llm.py
"""

import os
import time
import uuid
from contextlib import contextmanager
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# Tracer (same idea as file 02, trimmed for reuse)
# ============================================================

class Span:
    def __init__(self, name):
        self.name = name
        self.span_id = uuid.uuid4().hex[:8]
        self.attributes = {}
        self.children = []
        self.duration_ms = None
        self.error = None

    def set(self, **kwargs):
        self.attributes.update(kwargs)


class Tracer:
    def __init__(self):
        self.root = None
        self._stack = []

    @contextmanager
    def span(self, name):
        span = Span(name)
        if self._stack:
            self._stack[-1].children.append(span)
        else:
            self.root = span
        self._stack.append(span)
        start = time.perf_counter()
        try:
            yield span
        except Exception as e:
            span.error = repr(e)
            raise
        finally:
            span.duration_ms = (time.perf_counter() - start) * 1000
            self._stack.pop()

    def total_tokens(self):
        total = 0

        def walk(s):
            nonlocal total
            total += s.attributes.get("total_tokens", 0)
            for c in s.children:
                walk(c)

        if self.root:
            walk(self.root)
        return total

    def print_tree(self):
        print("\nTRACE")
        _print_span(self.root, "", True)
        print(f"\n  TOTAL tokens this request: {self.total_tokens()}")


def _print_span(span, prefix, is_last):
    connector = "└─ " if is_last else "├─ "
    status = "  ERROR" if span.error else ""
    attrs = "  " + " ".join(f"{k}={v}" for k, v in span.attributes.items()) if span.attributes else ""
    print(f"{prefix}{connector}{span.name}  ({span.duration_ms:.0f}ms){attrs}{status}")
    if span.error:
        print(f"{prefix}    ! {span.error}")
    child_prefix = prefix + ("   " if is_last else "│  ")
    for i, c in enumerate(span.children):
        _print_span(c, child_prefix, i == len(span.children) - 1)


# ============================================================
# The one wrapper that makes every LLM call observable
# ============================================================

def traced_chat(tracer, span_name, **kwargs):
    """Call the model inside a span and auto-record usage + timing."""
    with tracer.span(span_name) as s:
        resp = client.chat.completions.create(**kwargs)
        usage = resp.usage
        s.set(
            model=kwargs.get("model", MODEL),
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )
        return resp.choices[0].message.content


# ============================================================
# DEMO: a 2-step agent, fully traced
# ============================================================

def main():
    print("=" * 60)
    print("  Tracing real Groq calls — timing + tokens captured for free")
    print("=" * 60)

    tracer = Tracer()
    question = "Name one benefit of tracing an AI app. One sentence."

    with tracer.span("handle_request") as root:
        root.set(user="alice")

        plan = traced_chat(
            tracer, "llm.plan",
            model=MODEL,
            messages=[{"role": "user", "content": f"In one short line, plan how to answer: {question}"}],
        )

        traced_chat(
            tracer, "llm.answer",
            model=MODEL,
            messages=[
                {"role": "user", "content": f"Plan: {plan}\n\nNow answer: {question}"},
            ],
        )

    tracer.print_tree()

    print("\n  Notice: you didn't add token counting to each call by hand.")
    print("  Instrumenting ONE wrapper (traced_chat) made the whole run")
    print("  observable. Next (04): turn spans into JSON logs + metrics")
    print("  you could ship to a file or a real backend.")


if __name__ == "__main__":
    main()
