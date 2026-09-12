"""
Multiprocessing Basics — Use multiple CPU cores

Threading = 1 core, good for waiting (network/I/O)
Multiprocessing = multiple cores, good for heavy computation

This script shows the difference with a CPU-heavy task (math).

Run: python3 02_multiprocessing_basics.py
"""

import time
import os
import math
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


# ============================================================
# A CPU-HEAVY TASK (uses the processor, not the network)
# ============================================================

def heavy_computation(n: int) -> dict:
    """
    Simulate heavy CPU work: check if numbers are prime.
    This keeps the CPU busy — no waiting involved.
    """
    count = 0
    for i in range(2, n):
        if all(i % j != 0 for j in range(2, int(math.sqrt(i)) + 1)):
            count += 1
    return {"range": n, "primes_found": count, "pid": os.getpid()}


# ============================================================
# EXAMPLE 1: Sequential (1 core, one at a time)
# ============================================================

def demo_sequential():
    print("\n" + "=" * 60)
    print("  SEQUENTIAL — 1 core, one task at a time")
    print("=" * 60)

    tasks = [200_000, 200_000, 200_000, 200_000]  # 4 heavy tasks

    start = time.time()
    results = []
    for task in tasks:
        result = heavy_computation(task)
        results.append(result)
        print(f"   ✅ Done: {result['primes_found']} primes (PID: {result['pid']})")

    elapsed = time.time() - start
    print(f"\n   ⏱️  Total time: {elapsed:.2f} seconds")
    print(f"   All ran on same process (PID: {os.getpid()})")
    return elapsed


# ============================================================
# EXAMPLE 2: Threading (still 1 core — GIL blocks parallelism)
# ============================================================

def demo_threading():
    print("\n" + "=" * 60)
    print("  THREADING — Still 1 core (GIL prevents true parallel)")
    print("=" * 60)

    tasks = [200_000, 200_000, 200_000, 200_000]

    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(heavy_computation, tasks))

    for r in results:
        print(f"   ✅ Done: {r['primes_found']} primes (PID: {r['pid']})")

    elapsed = time.time() - start
    print(f"\n   ⏱️  Total time: {elapsed:.2f} seconds")
    print(f"   Same PID for all = same process = 1 core")
    print(f"   ⚠️  NOT faster than sequential for CPU work!")
    return elapsed


# ============================================================
# EXAMPLE 3: Multiprocessing (MULTIPLE cores — truly parallel!)
# ============================================================

def demo_multiprocessing():
    print("\n" + "=" * 60)
    print("  MULTIPROCESSING — Multiple cores (truly parallel!)")
    print("=" * 60)

    tasks = [200_000, 200_000, 200_000, 200_000]

    start = time.time()
    # ProcessPoolExecutor uses SEPARATE processes on different cores
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(heavy_computation, tasks))

    for r in results:
        print(f"   ✅ Done: {r['primes_found']} primes (PID: {r['pid']})")

    elapsed = time.time() - start
    print(f"\n   ⏱️  Total time: {elapsed:.2f} seconds")
    print(f"   Different PIDs = different processes = different cores!")
    print(f"   🚀 Should be ~4x faster than sequential!")
    return elapsed


# ============================================================
# COMPARISON
# ============================================================

def demo_comparison():
    print("\n" + "=" * 60)
    print("  COMPARISON — Sequential vs Threading vs Multiprocessing")
    print("  (CPU-heavy task: counting primes)")
    print("=" * 60)
    print(f"\n   Your CPU cores: {os.cpu_count()}")
    print(f"   Running 4 heavy tasks...\n")

    t_seq = demo_sequential()
    t_thread = demo_threading()
    t_multi = demo_multiprocessing()

    print("\n" + "=" * 60)
    print("  📊 RESULTS")
    print("=" * 60)
    print(f"""
   Sequential:      {t_seq:.2f}s  (baseline)
   Threading:       {t_thread:.2f}s  (same or slower — GIL!)
   Multiprocessing: {t_multi:.2f}s  (fastest — uses all cores)

   Speedup: {t_seq / t_multi:.1f}x faster with multiprocessing

   ┌─────────────────────────────────────────────────┐
   │ Sequential:      [████████████████████████████]  │
   │ Threading:       [████████████████████████████]  │  ← No speedup!
   │ Multiprocessing: [███████]                       │  ← ~4x faster!
   └─────────────────────────────────────────────────┘

   WHY?
   • Threading: GIL allows only 1 thread to run Python at a time
     → for CPU work, threads just take turns on 1 core
   • Multiprocessing: Each process has its OWN Python + GIL
     → truly runs on separate cores simultaneously
""")


# ============================================================
# WHEN TO USE WHAT — CHEAT SHEET
# ============================================================

def show_cheatsheet():
    print("""
   ┌──────────────────────────────────────────────────────────┐
   │              WHEN TO USE WHAT                            │
   ├──────────────────────────────────────────────────────────┤
   │                                                          │
   │  Task involves WAITING?          → Threading             │
   │  (API calls, downloads, DB)        (or async/await)      │
   │                                                          │
   │  Task involves COMPUTING?        → Multiprocessing       │
   │  (math, image processing,          (uses multiple cores) │
   │   data crunching, ML)                                    │
   │                                                          │
   │  Task is simple/short?           → Just run it normally  │
   │                                                          │
   ├──────────────────────────────────────────────────────────┤
   │                                                          │
   │  CODE DIFFERENCE (just one word!):                       │
   │                                                          │
   │  # For I/O (waiting):                                    │
   │  from concurrent.futures import ThreadPoolExecutor       │
   │                                                          │
   │  # For CPU (computing):                                  │
   │  from concurrent.futures import ProcessPoolExecutor      │
   │                                                          │
   │  # Usage is identical:                                   │
   │  with ___PoolExecutor(max_workers=4) as executor:        │
   │      results = executor.map(my_function, my_data)        │
   │                                                          │
   └──────────────────────────────────────────────────────────┘
""")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  ⚡ MULTIPROCESSING BASICS")
    print("=" * 60)
    print(f"   Your Mac has {os.cpu_count()} CPU cores")
    print("""
   Examples:
     1) Sequential (baseline)
     2) Threading (won't help for CPU work)
     3) Multiprocessing (uses all cores!)
     4) Full comparison (run all 3, see the difference)
     5) Cheat sheet (when to use what)
""")

    choice = input("   Choice (1-5): ").strip()

    if choice == "1":
        demo_sequential()
    elif choice == "2":
        demo_threading()
    elif choice == "3":
        demo_multiprocessing()
    elif choice == "4":
        demo_comparison()
    elif choice == "5":
        show_cheatsheet()
    else:
        print("Invalid choice.")
