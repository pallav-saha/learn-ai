"""
Threading Basics — Run multiple things at the same time

Threading = doing multiple tasks simultaneously in Python.

Without threading: Task A finishes, THEN Task B starts, THEN Task C starts
With threading:    Task A, B, and C all run AT THE SAME TIME

Run: python3 01_threading_basics.py
"""

import time
import threading
import concurrent.futures


# ============================================================
# EXAMPLE 1: Without threading (sequential)
# ============================================================

def slow_task(name: str, duration: int) -> str:
    """A task that takes some time (simulates an API call)."""
    print(f"   ⏳ {name} started (takes {duration}s)...")
    time.sleep(duration)  # Simulate waiting
    print(f"   ✅ {name} done!")
    return f"{name} result"


def demo_sequential():
    print("\n" + "=" * 60)
    print("  EXAMPLE 1: Sequential (one at a time)")
    print("=" * 60)

    start = time.time()

    # Each task waits for the previous one to finish
    result_a = slow_task("Task A", 2)
    result_b = slow_task("Task B", 2)
    result_c = slow_task("Task C", 2)

    elapsed = time.time() - start
    print(f"\n   Total time: {elapsed:.1f} seconds (expected ~6s)")
    print(f"   Results: {result_a}, {result_b}, {result_c}")


# ============================================================
# EXAMPLE 2: With threading (parallel)
# ============================================================

def demo_threaded():
    print("\n" + "=" * 60)
    print("  EXAMPLE 2: Threaded (all at the same time)")
    print("=" * 60)

    start = time.time()

    # ThreadPoolExecutor runs tasks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all 3 tasks — they START immediately, all at once
        future_a = executor.submit(slow_task, "Task A", 2)
        future_b = executor.submit(slow_task, "Task B", 2)
        future_c = executor.submit(slow_task, "Task C", 2)

        # .result() waits for each to finish and gets the return value
        result_a = future_a.result()
        result_b = future_b.result()
        result_c = future_c.result()

    elapsed = time.time() - start
    print(f"\n   Total time: {elapsed:.1f} seconds (expected ~2s, not 6!)")
    print(f"   Results: {result_a}, {result_b}, {result_c}")


# ============================================================
# EXAMPLE 3: Understanding what happens
# ============================================================

def demo_visualize():
    print("\n" + "=" * 60)
    print("  EXAMPLE 3: Visualizing parallel execution")
    print("=" * 60)

    def worker(name: str, duration: int):
        """Shows which thread is running."""
        thread_name = threading.current_thread().name
        print(f"   🟢 {name} STARTED on {thread_name}")
        time.sleep(duration)
        print(f"   🔴 {name} FINISHED on {thread_name}")
        return f"{name} done"

    print("\n   Watch the START/FINISH order:\n")

    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(worker, "API Call 1", 3): "API 1",
            executor.submit(worker, "API Call 2", 1): "API 2",  # Fastest
            executor.submit(worker, "API Call 3", 2): "API 3",
        }

        # as_completed gives results as soon as each finishes
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            result = future.result()
            print(f"   📬 Got result: {result} (at {time.time() - start:.1f}s)")

    elapsed = time.time() - start
    print(f"\n   Total: {elapsed:.1f}s (not 6s, because they overlapped!)")
    print("""
   Timeline:
   API Call 1: [████████████████████████████] 3s
   API Call 2: [████████]                     1s (finishes first!)
   API Call 3: [████████████████████]         2s
               ↑ all start at the same time
   """)


# ============================================================
# EXAMPLE 4: Real-world — Parallel API calls
# ============================================================

def demo_parallel_api():
    print("\n" + "=" * 60)
    print("  EXAMPLE 4: Real-world parallel API calls")
    print("=" * 60)

    def fake_api_call(url: str) -> dict:
        """Simulates calling different APIs."""
        # Simulate different response times
        delays = {
            "weather_api": 1.5,
            "news_api": 2.0,
            "stock_api": 1.0,
        }
        delay = delays.get(url, 1.0)
        time.sleep(delay)
        return {"url": url, "status": "success", "time": f"{delay}s"}

    apis_to_call = ["weather_api", "news_api", "stock_api"]

    # Sequential
    print("\n   📡 Sequential API calls:")
    start = time.time()
    sequential_results = []
    for api in apis_to_call:
        result = fake_api_call(api)
        sequential_results.append(result)
    print(f"   Time: {time.time() - start:.1f}s (sum of all delays)")

    # Parallel
    print("\n   📡 Parallel API calls:")
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        parallel_results = list(executor.map(fake_api_call, apis_to_call))
    print(f"   Time: {time.time() - start:.1f}s (only the slowest one)")

    print(f"\n   Sequential: ~4.5s (1.5 + 2.0 + 1.0)")
    print(f"   Parallel:   ~2.0s (max of 1.5, 2.0, 1.0)")
    print(f"   Speedup:    2.25x faster!")


# ============================================================
# EXAMPLE 5: Thread safety — the gotcha
# ============================================================

def demo_thread_safety():
    print("\n" + "=" * 60)
    print("  EXAMPLE 5: Thread Safety (the common bug)")
    print("=" * 60)

    # PROBLEM: Multiple threads modifying the same variable
    counter = {"value": 0}  # Shared between threads

    def increment_unsafe():
        """Each thread tries to add 1 to counter."""
        for _ in range(100000):
            counter["value"] += 1  # NOT SAFE — threads can overwrite each other

    print("\n   Running 2 threads, each adding 100,000 to a counter...")
    print("   Expected result: 200,000\n")

    # Run without protection
    counter["value"] = 0
    threads = [
        threading.Thread(target=increment_unsafe),
        threading.Thread(target=increment_unsafe),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"   ❌ Unsafe result: {counter['value']} (might not be 200,000!)")

    # SOLUTION: Use a Lock
    lock = threading.Lock()

    def increment_safe():
        """Thread-safe version using a lock."""
        for _ in range(100000):
            with lock:  # Only one thread can enter this block at a time
                counter["value"] += 1

    counter["value"] = 0
    threads = [
        threading.Thread(target=increment_safe),
        threading.Thread(target=increment_safe),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"   ✅ Safe result:   {counter['value']} (always 200,000)")

    print("""
   Why?
   Without lock: Thread A reads 5, Thread B reads 5,
                 both write 6 — one increment lost!
   
   With lock:    Thread A reads 5, writes 6 (Thread B waits),
                 Thread B reads 6, writes 7 — nothing lost!
   """)


# ============================================================
# KEY CONCEPTS SUMMARY
# ============================================================

def show_summary():
    print("\n" + "=" * 60)
    print("  📝 THREADING SUMMARY")
    print("=" * 60)
    print("""
   KEY CONCEPTS:

   1. Thread = a separate path of execution
      Your program normally runs one line at a time.
      Threads let multiple lines run simultaneously.

   2. ThreadPoolExecutor = easy way to manage threads
      executor.submit(fn, args) → starts a task
      future.result() → waits for and gets the answer

   3. When to use threads:
      ✅ Multiple API calls (network I/O)
      ✅ Multiple file reads/writes
      ✅ Multiple database queries
      ❌ Heavy math/computation (use multiprocessing instead)

   4. Thread safety:
      If threads READ shared data → safe
      If threads WRITE shared data → use a Lock

   5. Threading vs Async:
      Threading: Multiple threads, OS switches between them
      Async:     One thread, YOUR CODE switches during await
      Both solve the same problem (concurrency) differently.

   QUICK REFERENCE:
   ────────────────
   # Run 3 functions in parallel:
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
       future_a = executor.submit(func_a, arg1)
       future_b = executor.submit(func_b, arg2)
       future_c = executor.submit(func_c, arg3)
       result_a = future_a.result()  # waits and gets return value
       result_b = future_b.result()
       result_c = future_c.result()
""")


# ============================================================
# RUN ALL
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🧵 THREADING BASICS")
    print("=" * 60)
    print("""
   Examples:
     1) Sequential vs Threaded (see the time difference)
     2) Threaded (same thing, cleaner)
     3) Visualize parallel execution
     4) Real-world parallel API calls
     5) Thread safety (common bug)
     6) Show summary
     A) Run ALL
""")

    choice = input("   Choice: ").strip().upper()

    demos = {
        "1": demo_sequential,
        "2": demo_threaded,
        "3": demo_visualize,
        "4": demo_parallel_api,
        "5": demo_thread_safety,
        "6": show_summary,
    }

    if choice == "A":
        demo_sequential()
        demo_threaded()
        demo_visualize()
        demo_parallel_api()
        demo_thread_safety()
        show_summary()
    elif choice in demos:
        demos[choice]()
    else:
        print("Invalid choice.")
