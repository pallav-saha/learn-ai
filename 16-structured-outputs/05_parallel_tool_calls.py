"""
05 - Parallel Tool Calls

In file 03/04, the model made ONE tool call per response. But a model CAN request
MULTIPLE tool calls in a single response — e.g. "weather in Tokyo AND Paris AND London"
can produce 3 tool calls at once. You then run them (ideally in parallel) and feed all
results back together.

IMPORTANT (tested on Groq):
  - Not every model does this. gpt-oss-20b returned only 1 call for a 3-city request.
  - qwen/qwen3.8-27b returned all 3 calls at once (true parallel).
  So this file uses qwen for the parallel demo, and shows how to handle N tool calls.

Run:
    cd 16-structured-outputs && ../.venv/bin/python3 05_parallel_tool_calls.py
"""

import os
import json
import time
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
# This model reliably emits parallel tool calls on Groq (gpt-oss-20b does not).
MODEL = "qwen/qwen3.8-27b"


# ============================================================
# A tool that is SLOW (so parallel vs sequential timing is visible)
# ============================================================

def get_weather(city: str) -> str:
    time.sleep(1)  # pretend each weather API call takes 1 second
    fake = {"Tokyo": "18°C, cloudy", "Paris": "12°C, rainy", "London": "10°C, foggy"}
    return fake.get(city, f"Weather unavailable for {city}")


AVAILABLE_FUNCTIONS = {"get_weather": get_weather}

TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {"type": "object",
                       "properties": {"city": {"type": "string"}},
                       "required": ["city"]},
    },
}]


# ============================================================
# STEP 1: ask a question that needs MULTIPLE tool calls
# ============================================================

def get_parallel_tool_calls(question: str):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        tools=TOOLS,
        tool_choice="auto",
    )
    return response.choices[0].message.tool_calls or []


# ============================================================
# STEP 2a: run the tool calls SEQUENTIALLY (one after another)
# ============================================================

def run_sequential(tool_calls):
    results = []
    start = time.time()
    for tc in tool_calls:
        args = json.loads(tc.function.arguments)
        results.append(AVAILABLE_FUNCTIONS[tc.function.name](**args))
    elapsed = time.time() - start
    return results, elapsed


# ============================================================
# STEP 2b: run the tool calls IN PARALLEL (all at once)
# ============================================================

def run_parallel(tool_calls):
    start = time.time()
    # ThreadPoolExecutor runs the (I/O-bound) tool calls concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for tc in tool_calls:
            args = json.loads(tc.function.arguments)
            fn = AVAILABLE_FUNCTIONS[tc.function.name]
            futures.append(executor.submit(fn, **args))
        results = [f.result() for f in futures]
    elapsed = time.time() - start
    return results, elapsed


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  Parallel Tool Calls")
    print("=" * 60)
    print(f"  Model: {MODEL} (emits multiple tool calls at once)\n")

    question = "Get the current weather in Tokyo, Paris, and London."
    print(f"  User: {question}\n")

    tool_calls = get_parallel_tool_calls(question)
    print(f"  The model requested {len(tool_calls)} tool calls in ONE response:")
    for tc in tool_calls:
        print(f"    - {tc.function.name}({tc.function.arguments})")

    if len(tool_calls) < 2:
        print("\n  (This model returned <2 calls — parallelism not demonstrable here.)")
        return

    # Each weather call takes ~1s. Watch the timing difference.
    print("\n  Running SEQUENTIALLY (one at a time):")
    seq_results, seq_time = run_sequential(tool_calls)
    print(f"    Results: {seq_results}")
    print(f"    Time: {seq_time:.2f}s  (~1s per call, added up)")

    print("\n  Running IN PARALLEL (all at once):")
    par_results, par_time = run_parallel(tool_calls)
    print(f"    Results: {par_results}")
    print(f"    Time: {par_time:.2f}s  (all overlap → about as long as ONE call)")

    print(f"\n  Speedup: {seq_time / par_time:.1f}x faster by running them in parallel.")
    print("""
  KEY POINTS:
    - A model can return MANY tool calls in one response (message.tool_calls is a list).
    - Run INDEPENDENT calls in parallel (ThreadPoolExecutor) to cut latency.
    - Feed ALL results back (one 'tool' message per call, matched by tool_call_id)
      before asking the model for its final answer.
    - Only parallelize INDEPENDENT calls. If call B needs call A's result, they must
      stay sequential (the model usually splits those across separate turns anyway).
""")


if __name__ == "__main__":
    main()
