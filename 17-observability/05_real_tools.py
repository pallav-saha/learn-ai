"""
05 - The real tools (what you'd actually use in production)

You built a tracer, structured logs, and metrics by hand so the CONCEPTS are yours.
In real projects you don't hand-roll this — you use a library. They all implement
the exact same span/trace/attribute model you just built.

This file is a MAP, not a live demo (these need accounts / extra installs). It shows
the equivalent code so the jump from "my tracer" to "real tool" is obvious.

Run:
    cd 17-observability && ../.venv/bin/python3 05_real_tools.py
"""

# ============================================================
# The landscape (all implement span → trace → attributes)
# ============================================================

LANDSCAPE = """
  OpenTelemetry (OTel)   The open standard. Vendor-neutral spans/traces/metrics.
                         Most backends (Datadog, Grafana, Honeycomb) ingest OTel.
                         Choose this when you want zero lock-in.

  Langfuse               LLM-focused, open-source, self-hostable. Traces + token
                         cost + prompt management + evals. Great default for AI apps.

  LangSmith              From the LangChain team. Deep tracing, datasets, evals.
                         Best if you're already on LangChain.

  Phoenix (Arize)        Open-source, strong for RAG/agent debugging + eval views.
"""


# ---- What your traced_chat() (file 03) looks like in OpenTelemetry ----
OTEL_EXAMPLE = '''
from opentelemetry import trace
tracer = trace.get_tracer("my-agent")

def traced_chat(**kwargs):
    with tracer.start_as_current_span("llm.answer") as span:   # same "span" idea
        resp = client.chat.completions.create(**kwargs)
        span.set_attribute("llm.model", kwargs["model"])       # same "attributes"
        span.set_attribute("llm.total_tokens", resp.usage.total_tokens)
        return resp
'''

# ---- The same thing in Langfuse (decorator style) ----
LANGFUSE_EXAMPLE = '''
from langfuse.decorators import observe

@observe()                          # auto-creates a span for this function
def answer(question):               # nesting is automatic from the call stack
    return client.chat.completions.create(...)   # tokens/cost captured for you
'''


def main():
    print("=" * 60)
    print("  Observability tooling — same model you built, industrialized")
    print("=" * 60)
    print(LANDSCAPE)

    print("-" * 60)
    print("  Your file-03 wrapper, but in OpenTelemetry:")
    print("-" * 60)
    print(OTEL_EXAMPLE)

    print("-" * 60)
    print("  The same idea in Langfuse (decorator auto-instruments):")
    print("-" * 60)
    print(LANGFUSE_EXAMPLE)

    print("-" * 60)
    print("  How to choose")
    print("-" * 60)
    print("  - Want the open standard / no lock-in     → OpenTelemetry")
    print("  - Want LLM-specific traces + cost, OSS     → Langfuse")
    print("  - Already using LangChain                  → LangSmith")
    print("  - Debugging RAG/agents with eval views     → Phoenix")
    print()
    print("  The mental model never changes: a SPAN is a timed step with")
    print("  attributes; a TRACE is the tree of spans for one request.")
    print("  Everything you learned in 01-04 maps 1:1 onto these tools.")


if __name__ == "__main__":
    main()
