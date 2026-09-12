"""
try/except/finally  vs  Context Manager (@contextmanager)
=========================================================

Both guarantee CLEANUP runs (even on error). They do the SAME job.
In fact, @contextmanager USES try/finally internally.

The difference is REUSABILITY:
  - try/finally      = write the cleanup inline, REPEAT it everywhere you need it
  - context manager  = bundle that try/finally into a REUSABLE, named 'with' block

Run:
    cd 14-evaluation && ../.venv/bin/python3 tryfinally_vs_contextmanager.py

============================================================
THE KEY IDEA
============================================================
Same task = "time an operation and always log how long it took, even if it fails."

Watch the SAME task done both ways below, then run it to see identical behavior.
"""

import time
from contextlib import contextmanager


# ============================================================
# WAY 1: try / finally  — write the setup + cleanup INLINE, every time
# ============================================================

def demo_try_finally():
    print("=" * 58)
    print("  WAY 1: try/finally (inline, repeated at each call site)")
    print("=" * 58)

    # Call site 1
    start = time.time()                         # setup
    try:
        _ = sum(range(500_000))                 # the work
    finally:
        print(f"  op1 took {time.time() - start:.3f}s")   # cleanup

    # Call site 2 — SAME boilerplate copy-pasted
    start = time.time()                         # setup (repeated)
    try:
        _ = sum(range(1_000_000))               # the work
    finally:
        print(f"  op2 took {time.time() - start:.3f}s")   # cleanup (repeated)

    # Call site 3 — repeated AGAIN
    start = time.time()
    try:
        _ = sum(range(200_000))
    finally:
        print(f"  op3 took {time.time() - start:.3f}s")

    print("  Notice: the start/try/finally boilerplate is repeated 3 times.")
    print("  Change the logging format? You'd edit all 3 places.\n")


# ============================================================
# WAY 2: context manager — write setup + cleanup ONCE, reuse everywhere
# ============================================================

@contextmanager
def timer(label):
    start = time.time()          # setup — written ONCE
    try:
        yield
    finally:
        print(f"  {label} took {time.time() - start:.3f}s")   # cleanup — ONCE


def demo_context_manager():
    print("=" * 58)
    print("  WAY 2: context manager (setup/cleanup written once, reused)")
    print("=" * 58)

    with timer("op1"):
        _ = sum(range(500_000))

    with timer("op2"):
        _ = sum(range(1_000_000))

    with timer("op3"):
        _ = sum(range(200_000))

    print("  Notice: the timing logic lives in ONE place (timer()).")
    print("  Change the logging format? Edit ONE function.\n")


# ============================================================
# BOTH handle errors the same way (cleanup still runs)
# ============================================================

def demo_error_handling():
    print("=" * 58)
    print("  BOTH guarantee cleanup even on ERROR")
    print("=" * 58)

    # try/finally version
    print("  try/finally:")
    start = time.time()
    try:
        raise ValueError("boom")
    except ValueError:
        print("    caught error")
    finally:
        print(f"    cleanup ran ({time.time() - start:.3f}s)")

    # context manager version
    print("  context manager:")
    try:
        with timer("    failing_op"):
            raise ValueError("boom")
    except ValueError:
        print("    caught error (cleanup already ran above)")

    print("  Same guarantee — cleanup ALWAYS runs.\n")


# ============================================================
# NOTES / SUMMARY
# ============================================================

def summary():
    print("=" * 58)
    print("  NOTES: try/finally vs context manager")
    print("=" * 58)
    print("""
  SAME job:  both guarantee cleanup runs, even if the code errors.
             (@contextmanager literally uses try/finally inside.)

  DIFFERENCE:  reusability & readability
  ---------------------------------------------------------------
    try/finally
      - write setup + cleanup INLINE, repeat it at every call site
      - good for a ONE-OFF cleanup in a single place
      - downside: copy-paste boilerplate; change = edit many places

    context manager (@contextmanager)
      - bundle the setup/cleanup into ONE reusable, named function
      - use it anywhere with a clean 'with' block
      - good when the SAME setup/cleanup repeats in many places
      - change the logic = edit ONE function

  WHEN TO USE WHICH
  ---------------------------------------------------------------
    Use try/finally when:
      - cleanup is needed in just ONE spot (one-off)
      - Example: a single risky operation with a single cleanup

    Use a context manager when:
      - the SAME setup/cleanup pattern repeats in MANY places
      - you want a clean, named, self-documenting 'with' block
      - Examples: files (open/close), timers, DB connections,
        locks (acquire/release), tracing every LLM call

  WHY IT'S NEEDED (the real benefit)
  ---------------------------------------------------------------
    Reliability: cleanup is GUARANTEED — you can't forget it, and it
    runs even on exceptions. Context managers make that guarantee
    REUSABLE, so you don't copy-paste try/finally everywhere.

  REAL EXAMPLE (module 14):
    The observability tracer wraps EVERY LLM call to record timing/cost.
    Using try/finally would mean repeating that boilerplate at every
    call. A context manager (tracer.trace_llm) bundles it once, so each
    call is just:
        with tracer.trace_llm("name") as span:
            span["response"] = client.chat.completions.create(...)
""")


if __name__ == "__main__":
    print()
    demo_try_finally()
    demo_context_manager()
    demo_error_handling()
    summary()
