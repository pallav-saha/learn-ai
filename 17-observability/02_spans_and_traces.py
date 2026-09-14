"""
02 - Spans & Traces (build the core idea yourself)

A SPAN is one timed, named unit of work: it has a name, a start time, a duration,
and some attributes (key/value data you attach). Examples of spans:
    "llm.plan"  (0.42s)   "tool.get_weather" (0.19s)   "llm.answer" (0.55s)

A TRACE is all the spans for ONE request, usually nested to show parent/child:

    trace: handle_request                      (1.30s)
      ├─ span: llm.plan                        (0.42s)
      ├─ span: tool.get_weather                (0.19s)
      └─ span: llm.answer                      (0.55s)

That tree is the single most useful debugging artifact in AI systems: you instantly
see WHAT ran, in WHAT ORDER, how LONG each took, and where it broke.

Here we implement a ~40-line tracer with just the stdlib so the concept is concrete.
Real tools (OpenTelemetry, Langfuse, LangSmith) are this same idea, industrialized.

Run:
    cd 17-observability && ../.venv/bin/python3 02_spans_and_traces.py
"""

import time
import uuid
from contextlib import contextmanager


# ============================================================
# A minimal tracer: spans as a tree, timed with a context manager
# ============================================================

class Span:
    def __init__(self, name):
        self.name = name
        self.span_id = uuid.uuid4().hex[:8]
        self.attributes = {}
        self.children = []
        self.start = None
        self.duration_ms = None
        self.error = None

    def set(self, **kwargs):
        """Attach structured data to the span (tokens, model, args, etc.)."""
        self.attributes.update(kwargs)


class Tracer:
    def __init__(self):
        self.root = None
        self._stack = []          # tracks the current parent span
    """
    with tracer.span("handle_request"):      # push → stack: [handle_request]
        with tracer.span("llm.plan"):         # push → stack: [handle_request, llm.plan]
            ...
        # llm.plan block exits → pop → stack: [handle_request]
        with tracer.span("tool.get_weather"): # top is handle_request → correct parent
            ...
        # exits → pop → stack: [handle_request]
    # handle_request exits → pop → stack: []

    Notice the effect: because llm.plan was popped when its block ended, tool.get_weather sees handle_request on top again and becomes its child (a sibling of llm.plan), not a child of llm.plan. Without the pop, tool.get_weather would wrongly nest under llm.plan.
    """


    @contextmanager
    def span(self, name):
        span = Span(name)
        # Link into the tree: whoever is on top of the stack is the parent
        if self._stack:
            self._stack[-1].children.append(span)
        else:
            self.root = span

        self._stack.append(span)
        span.start = time.perf_counter()
        try:
            yield span
        except Exception as e:
            span.error = repr(e)   # record failures ON the span
            raise
        finally:
            span.duration_ms = (time.perf_counter() - span.start) * 1000
            self._stack.pop()

    def print_tree(self):
        print("\nTRACE")
        _print_span(self.root, prefix="", is_last=True)


def _print_span(span, prefix, is_last):
    connector = "└─ " if is_last else "├─ "
    status = "  ERROR" if span.error else ""
    attrs = ""
    if span.attributes:
        attrs = "  " + " ".join(f"{k}={v}" for k, v in span.attributes.items())
    print(f"{prefix}{connector}{span.name}  ({span.duration_ms:.0f}ms){attrs}{status}")
    if span.error:
        print(f"{prefix}    ! {span.error}")

    child_prefix = prefix + ("   " if is_last else "│  ")
    for i, child in enumerate(span.children):
        _print_span(child, child_prefix, is_last=(i == len(span.children) - 1))


# ============================================================
# DEMO: trace a fake multi-step agent (no network needed)
# ============================================================

def main():
    print("=" * 60)
    print("  A hand-built tracer: spans nested into one trace")
    print("=" * 60)

    tracer = Tracer()

    with tracer.span("handle_request") as root:
        root.set(user="alice")

        with tracer.span("llm.plan") as s:
            time.sleep(0.15)
            s.set(model="gpt-oss-20b", tokens=42)

        with tracer.span("tool.get_weather") as s:
            time.sleep(0.08)
            s.set(city="Tokyo")

        with tracer.span("llm.answer") as s:
            time.sleep(0.22)
            s.set(model="gpt-oss-20b", tokens=88)

    tracer.print_tree()

    print("\n  Read the tree top-to-bottom: you can SEE the slowest step")
    print("  (llm.answer) and every step's data. That's a trace.")
    print("\n  Next (03): wire this tracer around REAL Groq calls +")
    print("  capture token usage automatically.")


if __name__ == "__main__":
    main()
