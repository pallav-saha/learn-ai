"""
06 - Streaming + Guardrails Tension

THE PROBLEM:
  Output guardrails need the FULL answer to check it (is it toxic? does it leak PII?).
  But streaming shows tokens to the user AS they arrive — before the full answer exists.
  So you can't fully guard a streamed response before the user starts seeing it.

  This is a genuine tradeoff. This file shows the 3 common strategies:

    A) BUFFER-THEN-CHECK : collect the whole answer, guard it, THEN show it.
                           Safe, but you lose the streaming "instant" feel.
    B) STREAM-THEN-RETRACT: stream live, but if a guardrail fails at the end,
                           replace/blank the message. Fast, but the user may
                           briefly see bad content.
    C) CHUNK-CHECK       : check each sentence/chunk as it completes before
                           showing it. Middle ground: small delay, catches issues
                           before most of the bad text is shown.

Run:
    cd 15-guardrails && ../.venv/bin/python3 06_streaming_guardrail_tension.py
"""

import os
import re
import time
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

# A simple PII check (reused from earlier files) to act as our "guardrail"
PII_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def has_pii(text: str) -> bool:
    return bool(PII_RE.search(text))


# ============================================================
# STRATEGY A: BUFFER-THEN-CHECK (safe, but no live streaming)
# ============================================================

def strategy_buffer_then_check(question: str):
    print("  Strategy A: BUFFER-THEN-CHECK")
    print("  (collect full answer -> guard it -> then show)\n")

    # Stream internally but DON'T show anything yet — just accumulate
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        stream=True, max_tokens=120,
    )
    full = ""
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            full += token
    # Now the full answer exists — run the guardrail
    if has_pii(full):
        print("    Guardrail failed (PII) -> user sees fallback, never the raw answer")
        print("    User sees: [blocked]")
    else:
        print("    Guardrail passed -> NOW show the answer:")
        print(f"    User sees: {full[:100]}...")
    print("    Tradeoff: fully safe, but the user waited with NO live tokens.\n")


# ============================================================
# STRATEGY B: STREAM-THEN-RETRACT (fast, but may briefly show bad text)
# ============================================================

def strategy_stream_then_retract(question: str):
    print("  Strategy B: STREAM-THEN-RETRACT")
    print("  (show tokens live -> if guardrail fails at end, retract)\n")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        stream=True, max_tokens=120,
    )
    full = ""
    print("    Live: ", end="")
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            full += token
            print(token, end="", flush=True)  # user sees it IMMEDIATELY
    print()  # newline

    # Guardrail runs AFTER streaming finished
    if has_pii(full):
        print("    Guardrail failed -> RETRACT: replace the shown message")
        print("    (in a UI you'd blank/replace it: '[message removed]')")
    else:
        print("    Guardrail passed -> keep the message")
    print("    Tradeoff: instant feel, but user may briefly see bad content.\n")


# ============================================================
# STRATEGY C: CHUNK-CHECK (middle ground — check per sentence)
# ============================================================

def strategy_chunk_check(question: str):
    print("  Strategy C: CHUNK-CHECK")
    print("  (buffer a sentence -> guard it -> show it -> repeat)\n")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": question}],
        stream=True, max_tokens=120,
    )
    buffer = ""
    print("    Output: ", end="")
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if not token:
            continue
        buffer += token
        # When we complete a sentence (hit . ! ?), guard it, then release it
        if token.endswith((".", "!", "?", "\n")):
            if has_pii(buffer):
                print("[chunk blocked]", end="", flush=True)  # don't show this chunk
            else:
                print(buffer, end="", flush=True)             # safe -> show it
            buffer = ""
    if buffer:  # leftover partial sentence
        print(buffer, end="")
    print()
    print("    Tradeoff: small delay per sentence, but catches bad chunks")
    print("    BEFORE most of the bad text is shown. Good balance.\n")


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 62)
    print("  Streaming + Guardrails Tension — 3 strategies")
    print("=" * 62)
    print("""
  Core problem: output guardrails need the FULL answer, but streaming
  shows tokens before the full answer exists. Pick your tradeoff:
""")

    question = "In one short paragraph, explain what an API is."

    strategy_buffer_then_check(question)
    strategy_stream_then_retract(question)
    strategy_chunk_check(question)

    print("=" * 62)
    print("  WHICH TO USE?")
    print("=" * 62)
    print("""
    Buffer-then-check   -> safety-critical apps where showing bad text is
                           unacceptable (medical, legal, kids' apps).
    Stream-then-retract -> low-risk apps where speed matters most and a brief
                           flash of bad text is tolerable (retracted fast).
    Chunk-check         -> the common middle ground: guard sentence-by-sentence,
                           small delay, catches issues before they fully show.

    There's NO perfect answer — it's a genuine safety-vs-speed tradeoff.
""")


if __name__ == "__main__":
    main()
