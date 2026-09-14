"""
01 - Why Observability? (the problem before the solution)

You can now build agents (03, 16), evaluate them (14), and guard them (15).
But when a real agent runs in production and something goes wrong, can you answer:

    - WHICH step failed? (the LLM call? a tool? parsing?)
    - HOW LONG did each step take? (where's the latency?)
    - HOW MANY tokens did the whole run burn? (where's the cost?)
    - WHAT did the model actually see and return at each step?

With plain `print()` you get scattered lines with no structure, no timing, and no
way to group "everything that happened in ONE user request". That's the gap
observability fills.

Three words you'll hear constantly:
    - LOG   : a single timestamped event ("called get_weather")
    - METRIC: a number you track over time (latency ms, tokens, error rate)
    - TRACE : the full story of ONE request, made of nested SPANS (steps)

This file shows the PAIN of debugging with only prints, so the next files land.

Run:
    cd 17-observability && ../.venv/bin/python3 01_why_observability.py
"""

import os
import time
import random
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# A tiny "agent" that does a few steps — logged with bare prints
# ============================================================

def flaky_tool(city: str) -> str:
    """Pretend this hits an external API that is sometimes slow / fails."""
    time.sleep(random.uniform(0.1, 0.4))
    if random.random() < 0.3:
        raise RuntimeError("weather API timed out")
    return f"{city}: 20C, clear"


def run_agent_with_prints(question: str):
    print("start handling request")
    print("calling llm to plan")

    plan = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"In 1 short line, plan how to answer: {question}"}],
    )
    print("got plan:", plan.choices[0].message.content)

    print("calling tool")
    try:
        result = flaky_tool("Tokyo")
        print("tool ok:", result)
    except Exception as e:
        print("tool FAILED:", e)
        result = "unknown"

    print("calling llm for final answer")
    final = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Answer '{question}' using: {result}"}],
    )
    print("final:", final.choices[0].message.content)
    print("done")


def main():
    print("=" * 60)
    print("  Debugging an agent with ONLY print() — notice the problems")
    print("=" * 60, "\n")

    run_agent_with_prints("What's the weather in Tokyo?")

    print("\n" + "-" * 60)
    print("  What's MISSING from those prints?")
    print("-" * 60)
    print("  1. No timing   — which step was slow? no idea.")
    print("  2. No tokens   — how much did this cost? no idea.")
    print("  3. No grouping — if 100 users hit this at once, whose")
    print("     prints are whose? they'd interleave into chaos.")
    print("  4. No structure— can't filter, aggregate, or store these.")
    print("\n  Next (02): we add a 'span' — a timed, named, structured step.")


if __name__ == "__main__":
    main()
