# 07 - Threading & Multiprocessing

## What's in this folder
- `threading_basics.py` — Threading demos (parallel I/O tasks, thread safety)
- `multiprocessing_basics.py` — Multiprocessing demo (use multiple CPU cores)

## Run
```bash
cd 07-threading && ../.venv/bin/python3 threading_basics.py
cd 07-threading && ../.venv/bin/python3 multiprocessing_basics.py
```

## Key Q&A

**Threading vs Multiprocessing?**
- Threading = 1 core, good for WAITING (API calls, network, file I/O)
- Multiprocessing = multiple cores, good for COMPUTING (math, data processing)

**Do threads use multiple cores in Python?**
No. Python's GIL (Global Interpreter Lock) only allows 1 thread to execute at a time. Threads are useful because during network waits, the CPU is idle anyway.

**When is threading faster?**
When tasks are waiting (not computing). 3 API calls sequentially = 9 seconds. With threads = 3 seconds (all wait at the same time).

**How to use:**
```python
from concurrent.futures import ThreadPoolExecutor   # for I/O
from concurrent.futures import ProcessPoolExecutor  # for CPU
```
Same API — just swap the class name.

**Thread safety?**
Multiple threads READING shared data = safe. WRITING = use a Lock.

**Lambda + threading?**
1 Lambda with threads for API calls = cheapest. Threads don't cost extra — same Lambda just finishes faster (less billed time).

**Lambda + multiprocessing?**
More memory = more cores on Lambda. 1769MB = 1 core, 7076MB = 4 cores.
