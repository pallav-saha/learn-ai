"""
03 - Output Guardrails

Input checks can't predict everything. After the LLM responds, inspect the OUTPUT
before it reaches the user:

  - PII LEAK   : did the answer contain emails/phones/SSNs/cards? (redact)
  - TOXICITY   : is the answer harmful/offensive? (LLM classifier)
  - GROUNDING  : (RAG) does the answer stick to the provided context? (anti-hallucination)
  - REFUSAL    : should we replace a bad answer with a safe fallback message?

Run:
    cd 15-guardrails && ../.venv/bin/python3 03_output_guardrails.py
"""

import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

SAFE_FALLBACK = "I'm sorry, I can't provide that response. Please rephrase your request."


# ============================================================
# GUARDRAIL 1: PII leak in output (regex — fast)
# ============================================================

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
}


def check_output_pii(text: str) -> dict:
    found = {}
    for label, pattern in PII_PATTERNS.items():
        if re.findall(pattern, text):
            found[label] = True
    return {"clean": len(found) == 0, "found": list(found.keys())}


def redact(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[REDACTED_{label.upper()}]", text)
    return text


# ============================================================
# GUARDRAIL 2: toxicity (LLM classifier)
# ============================================================

def check_toxicity(text: str) -> dict:
    prompt = f"""Classify if the TEXT is toxic, harmful, hateful, or unsafe.

TEXT: {text}

Respond ONLY as JSON: {{"toxic": true/false, "category": "<none|hate|violence|self-harm|harassment|other>"}}"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# GUARDRAIL 3: grounding (RAG anti-hallucination)
# ============================================================
# Same idea as module 14's faithfulness, used here as a live output guardrail.

def check_grounding(context: str, answer: str) -> dict:
    prompt = f"""Does the ANSWER contain ONLY information supported by the CONTEXT?

CONTEXT: {context}

ANSWER: {answer}

Respond ONLY as JSON: {{"grounded": true/false, "reason": "<short>"}}"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# DEMO
# ============================================================

def screen_output(output: str, context: str = None):
    """Run output guardrails, return the safe-to-send text (or fallback)."""
    print(f"\n  Output: {output[:70]}{'...' if len(output) > 70 else ''}")

    # 1. PII (free, first)
    pii = check_output_pii(output)
    if not pii["clean"]:
        print(f"    PII guardrail: found {pii['found']} → redacting")
        output = redact(output)
        print(f"    Redacted: {output[:70]}...")

    # 2. Toxicity (LLM)
    tox = check_toxicity(output)
    if tox["toxic"]:
        print(f"    Toxicity guardrail: BLOCKED (category: {tox['category']}) → fallback")
        return SAFE_FALLBACK

    # 3. Grounding (only if context provided — RAG)
    if context:
        g = check_grounding(context, output)
        if not g["grounded"]:
            print(f"    Grounding guardrail: BLOCKED (hallucination) — {g['reason']} → fallback")
            return SAFE_FALLBACK
        print(f"    Grounding guardrail: passed (grounded in context)")

    print(f"    All output guardrails passed → safe to send")
    return output


def main():
    print("=" * 60)
    print("  Output Guardrails — inspect the answer before sending")
    print("=" * 60)

    # 1. Clean output
    print("\n  [1] Clean, safe answer:")
    screen_output("You can substitute butter with olive oil in most recipes.")

    # 2. Output with PII (gets redacted)
    print("\n  [2] Answer that leaked PII:")
    screen_output("Sure! Contact our chef at chef@example.com or 555-987-6543.")

    # 3. RAG grounded answer (passes grounding)
    print("\n  [3] RAG answer that IS grounded:")
    screen_output(
        "The return window is 30 days with a receipt.",
        context="Returns are accepted within 30 days of purchase with a valid receipt.",
    )

    # 4. RAG hallucination (fails grounding → fallback)
    print("\n  [4] RAG answer that HALLUCINATES (not in context):")
    screen_output(
        "You can return items within 90 days and get a free gift card.",
        context="Returns are accepted within 30 days of purchase with a valid receipt.",
    )

    # 5. TOXIC answer → REFUSAL (replaced with safe fallback)
    print("\n  [5] TOXIC answer → REFUSAL (guardrail replaces it):")
    final = screen_output("You're an idiot and I hate helping people like you.")
    print(f"    What the USER actually receives: {final!r}")
    print("    ^ This is a REFUSAL: the bad answer was replaced by SAFE_FALLBACK.")

    print("\n  Output guardrails catch what input checks can't predict:")
    print("    leaked PII, toxic content, and hallucinations.")
    print("  REFUSAL = when a guardrail blocks, return SAFE_FALLBACK instead of the")
    print("  bad answer. That fallback string IS the refusal shown to the user.")


if __name__ == "__main__":
    main()
