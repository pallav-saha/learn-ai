"""
04 - Structured logs & metrics (make it queryable + aggregatable)

A trace tree is great for reading ONE request. But in production you have thousands
of requests and you want to ask:
    - "What's my p95 latency?"
    - "What's the error rate?"
    - "How many tokens did I burn this hour?"

You can't answer those from pretty-printed trees. You need:
    - STRUCTURED LOGS: each span emitted as one JSON line (machine-readable) so a
      log system can index and search it. This is why "print()" doesn't scale —
      JSON logs do.
    - METRICS: numbers rolled up across many spans (count, avg, p95, error rate).

This file emits spans as JSON lines and then computes simple metrics over them —
exactly what a real backend does, minus the network.

Run:
    cd 17-observability && ../.venv/bin/python3 04_structured_logs_and_metrics.py
"""

import json
import time
import random
import statistics


# ============================================================
# Emit each span as ONE JSON line (structured logging)
# ============================================================
# In real systems these lines go to stdout → collected by the platform
# (CloudWatch, Loki, Datadog...) and indexed. Here we just collect them
# in a list and also print them so you can see the shape.

def emit(record: dict, sink: list):
    line = json.dumps(record)
    print(line)          # a real app logs to stdout; the platform scrapes it
    sink.append(record)


def simulate_llm_span(trace_id: str, name: str, sink: list):
    """Fake an LLM step so we can generate many records without spending tokens."""
    start = time.perf_counter()
    latency = random.uniform(0.05, 0.6)
    time.sleep(latency * 0.1)                 # keep the demo fast; scale down sleep
    failed = random.random() < 0.15
    tokens = random.randint(30, 200)

    record = {
        "trace_id": trace_id,
        "span": name,
        "duration_ms": round(latency * 1000, 1),
        "total_tokens": tokens,
        "status": "error" if failed else "ok",
        "ts": round(time.time(), 3),
    }
    emit(record, sink)
    return record


# ============================================================
# Roll spans up into METRICS
# ============================================================

def compute_metrics(records: list):
    latencies = sorted(r["duration_ms"] for r in records)
    tokens = sum(r["total_tokens"] for r in records)
    errors = sum(1 for r in records if r["status"] == "error")
    n = len(records)

    def pct(data, p):
        if not data:
            return 0.0
        k = max(0, min(len(data) - 1, int(round((p / 100) * (len(data) - 1)))))
        return data[k]

    return {
        "requests": n,
        "error_rate": round(errors / n, 3) if n else 0.0,
        "latency_avg_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
        "latency_p50_ms": round(pct(latencies, 50), 1),
        "latency_p95_ms": round(pct(latencies, 95), 1),
        "total_tokens": tokens,
    }


def main():
    print("=" * 60)
    print("  Structured JSON logs (one line per span):")
    print("=" * 60)

    sink = []
    # Simulate 20 requests, each a single traced LLM span
    for i in range(20):
        simulate_llm_span(trace_id=f"req-{i:03d}", name="llm.answer", sink=sink)

    print("\n" + "=" * 60)
    print("  Metrics rolled up across all 20 requests:")
    print("=" * 60)
    metrics = compute_metrics(sink)
    for k, v in metrics.items():
        print(f"  {k:16} = {v}")

    print("\n  Why this matters:")
    print("  - JSON lines are searchable/filterable (find all status=error).")
    print("  - p95 latency reveals the slow tail avg hides.")
    print("  - error_rate + tokens are your reliability + cost dashboards.")
    print("\n  Next (05): the real tools that do all of this for you.")


if __name__ == "__main__":
    main()
