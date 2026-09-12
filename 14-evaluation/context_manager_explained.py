"""
Context Managers & @contextmanager — Explained (for revision)

This file explains the 'with' statement and the @contextmanager decorator
used in 04_observability.py — with simple, runnable examples.

Run:
    cd 14-evaluation && ../.venv/bin/python3 context_manager_explained.py

============================================================
WHAT IS A CONTEXT MANAGER?
============================================================
A context manager is anything you use with a 'with' block. It guarantees:
  - SETUP runs at the start
  - CLEANUP runs at the end (ALWAYS — even if the code inside crashes)

You already use them:
    with open("file.txt") as f:   # setup: open the file
        data = f.read()
    # cleanup: file automatically closed, even if read() errored

============================================================
WHY @contextmanager?
============================================================
Normally, making your own 'with'-compatible object needs a class with
__enter__ and __exit__ methods (verbose). @contextmanager lets you do it
with a simple FUNCTION + yield instead.

The yield splits the function into two halves:
    before yield  =  SETUP     (runs when entering the 'with')
    after yield   =  CLEANUP    (runs when exiting the 'with', even on error)

============================================================
WHEN TO USE IT (use cases)
============================================================
Use a context manager whenever you have PAIRED setup/cleanup that must
ALWAYS run together — "do X, then always undo X afterwards":

  - Files:        open  -> always close
  - Timers:       start -> always record elapsed (observability!)
  - DB:           open connection / begin transaction -> always commit/rollback + close
  - Locks:        acquire -> always release (threading)
  - Temp changes: change a setting -> always restore it
  - Resources:    allocate -> always free

The benefit: cleanup is GUARANTEED. You can't forget it, and it runs even
if an exception happens inside the block. That's why 04_observability.py uses
it — the timing/logging ALWAYS gets recorded, whether the LLM call succeeds or fails.
"""

import time
from contextlib import contextmanager


# ============================================================
# EXAMPLE 1: the simplest possible context manager
# ============================================================

@contextmanager
def simple_block():
    print("  1. SETUP    (before yield)")
    yield "hello"      # whatever you yield becomes the 'as x' value
    print("  3. CLEANUP  (after yield)")


def demo_1():
    print("=" * 55)
    print("  EXAMPLE 1: setup -> body -> cleanup order")
    print("=" * 55)
    with simple_block() as value:
        print(f"  2. BODY runs, got: '{value}'")
    print("  (notice cleanup ran automatically at the end)\n")


# ============================================================
# EXAMPLE 2: a timer (exactly what observability does)
# ============================================================

@contextmanager
def timer(label):
    start = time.time()          # SETUP: start timing
    try:
        yield                    # BODY runs here
    finally:
        elapsed = time.time() - start   # CLEANUP: always record
        print(f"  '{label}' took {elapsed:.3f}s")


def demo_2():
    print("=" * 55)
    print("  EXAMPLE 2: a timer (like the LLM tracer)")
    print("=" * 55)
    with timer("some work"):
        # pretend to do work
        total = sum(range(1_000_000))
    print("  The timer recorded automatically — no manual stop needed.\n")


# ============================================================
# EXAMPLE 3: cleanup runs EVEN ON ERROR (the key benefit)
# ============================================================

@contextmanager
def safe_block():
    print("  SETUP: acquired a resource")
    try:
        yield
    except Exception as e:
        print(f"  CAUGHT an error inside the block: {e}")
        raise                    # re-raise so the caller still sees it
    finally:
        print("  CLEANUP: released the resource (ran despite the error!)")


def demo_3():
    print("=" * 55)
    print("  EXAMPLE 3: cleanup runs even if the body crashes")
    print("=" * 55)
    try:
        with safe_block():
            print("  BODY: about to crash...")
            raise ValueError("boom!")
    except ValueError:
        print("  (the error still reached the caller, as expected)")
    print("  KEY POINT: cleanup ALWAYS runs — that's why it's reliable.\n")


# ============================================================
# EXAMPLE 4: yielding a value the body can modify
#            (this is exactly the tracer pattern from 04_observability.py)
# ============================================================

@contextmanager
def trace(name):
    span = {"name": name, "start": time.time()}   # SETUP
    try:
        yield span                                # hand the dict to the body
    finally:
        span["latency"] = round(time.time() - span["start"], 3)  # CLEANUP
        print(f"  Recorded span: {name} | latency={span['latency']}s | "
              f"result={span.get('result')}")


def demo_4():
    print("=" * 55)
    print("  EXAMPLE 4: the tracer pattern (yield a dict, body fills it)")
    print("=" * 55)
    with trace("fake_llm_call") as span:
        time.sleep(0.2)                # pretend LLM call
        span["result"] = "some answer" # body writes into the span
    print("  The body filled in span['result']; cleanup recorded the timing.\n")


# ============================================================
# BONUS: the class-based equivalent (what @contextmanager saves you from)
# ============================================================

class TimerClass:
    """Same as the timer above, but written as a class. More verbose."""
    def __init__(self, label):
        self.label = label

    def __enter__(self):          # SETUP (like 'before yield')
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # CLEANUP (like 'after yield')
        elapsed = time.time() - self.start
        print(f"  (class version) '{self.label}' took {elapsed:.3f}s")
        # return False = let any exception propagate


def demo_bonus():
    print("=" * 55)
    print("  BONUS: the class-based way (@contextmanager avoids this verbosity)")
    print("=" * 55)
    with TimerClass("class work"):
        sum(range(500_000))
    print("  Both do the same thing — @contextmanager is just shorter.\n")


# ============================================================
# EXAMPLE 5: the "PAUSE and RESUME" idea (the key mental model)
# ============================================================
# IMPORTANT: it's NOT "first time runs try, next time runs finally".
# It's ONE single run that PAUSES at yield and RESUMES into finally.
# yield freezes the function mid-execution (like the generators lesson).

@contextmanager
def show_pause_resume():
    print("    [A] setup runs (before yield)")
    try:
        print("    [B] about to yield -> FUNCTION PAUSES here")
        yield
        # ^ execution FREEZES at yield and hands control to the with-body.
        #   It does NOT continue past yield until the with-body finishes.
    finally:
        print("    [D] function RESUMED past yield -> cleanup runs")


def demo_5():
    print("=" * 55)
    print("  EXAMPLE 5: PAUSE at yield, RESUME into finally (one run)")
    print("=" * 55)
    with show_pause_resume():
        print("    [C] with-body runs (function is paused, waiting here)")
    print("""
  Order was: A -> B -> (pause) -> C -> (resume) -> D

  It's ONE call, not two:
    - runs up to yield (setup), then PAUSES
    - your with-body runs
    - when the body ends, the function RESUMES right after yield -> finally

  Analogy (bookmark in a book):
    read up to page 10 (yield) -> put a bookmark, set the book down
    do something else (the with-body)
    come back to the bookmark (page 10) -> finish reading (finally)
    You read the book ONCE, with a pause in the middle — not twice.
""")


# ============================================================
# SUMMARY
# ============================================================

def summary():
    print("=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    print("""
  @contextmanager = build a 'with' block from a simple function.

  Structure:
      @contextmanager
      def my_thing():
          # SETUP (runs on entering 'with')
          try:
              yield <value>   # <value> becomes 'as x'; body runs here
          finally:
              # CLEANUP (runs on exit — ALWAYS, even on error)

  Execution order (ONE run that pauses and resumes — NOT two runs):
      1. 'with' line runs setup up to yield, then PAUSES
      2. body of the with-block runs (function is frozen at yield)
      3. body ends -> function RESUMES past yield -> cleanup (finally) runs
      (yield freezes the function mid-execution, like a generator)

  Use it for PAIRED setup/cleanup that must always run together:
      files, timers, DB connections, locks, temp settings, tracing.

  Why it's great: cleanup is GUARANTEED. You can't forget it, and it
  runs even if the code inside raises an exception.
""")


if __name__ == "__main__":
    print()
    demo_1()
    demo_2()
    demo_3()
    demo_4()
    demo_bonus()
    demo_5()
    summary()
