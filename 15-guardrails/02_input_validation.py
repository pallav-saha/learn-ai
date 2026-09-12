"""
02 - Input Validation

Before you spend money on an LLM call, reject bad inputs cheaply. These checks are
fast (no LLM needed for most) and run FIRST:

  - LENGTH      : too short (empty) or too long (token/cost abuse)
  - EMPTY/JUNK  : blank or gibberish
  - OFF-TOPIC   : outside your app's domain (optional LLM check)
  - PII IN INPUT: user pasted sensitive data (warn/redact before sending to the LLM)
  - RATE/ABUSE  : (covered in module 13 — per-user rate limits)

Rejecting early = cheaper, faster, safer.

Run:
    cd 15-guardrails && ../.venv/bin/python3 02_input_validation.py
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

# Config
MIN_LENGTH = 3
MAX_LENGTH = 2000   # characters (rough proxy for token/cost control)


# ============================================================
# CHECK 1: length (cheapest — do first)
# ============================================================

def check_length(text: str) -> dict:
    text = text.strip()
    if len(text) < MIN_LENGTH:
        return {"ok": False, "reason": f"Too short (< {MIN_LENGTH} chars)"}
    if len(text) > MAX_LENGTH:
        return {"ok": False, "reason": f"Too long (> {MAX_LENGTH} chars) — possible abuse"}
    return {"ok": True, "reason": "length ok"}


# ============================================================
# CHECK 2: PII in the input (regex — fast)
# ============================================================
# Detect sensitive data the user pasted, so you can redact/warn before sending upstream.

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
}


def check_pii(text: str) -> dict:
    found = {}
    for label, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            found[label] = len(matches)
    return {"ok": len(found) == 0, "found": found}


def redact_pii(text: str) -> str:
    """Replace detected PII with placeholders."""
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[REDACTED_{label.upper()}]", text)
    return text


# ============================================================
# CHECK 3: on-topic (LLM — only if cheap checks passed)
# ============================================================

def check_on_topic(text: str, domain: str = "cooking and recipes") -> dict:
    prompt = f"""Is the following user question about {domain}? Answer strictly.

QUESTION: {text}

Respond ONLY as JSON: {{"on_topic": true/false}}"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# THE VALIDATION PIPELINE — cheap checks first, LLM last
# ============================================================

def validate_input(text: str, domain="cooking and recipes") -> dict:
    # 1. Length (free)
    length = check_length(text)
    if not length["ok"]:
        return {"valid": False, "stage": "length", "reason": length["reason"]}

    # 2. PII (free) — here we redact rather than reject
    pii = check_pii(text)
    cleaned = text
    if not pii["ok"]:
        cleaned = redact_pii(text)  # scrub before sending to the LLM

    # 3. On-topic (costs an LLM call — do last)
    topic = check_on_topic(text, domain)
    if not topic["on_topic"]:
        return {"valid": False, "stage": "off_topic", "reason": f"Not about {domain}"}

    return {"valid": True, "cleaned_input": cleaned, "pii_found": pii["found"]}


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  Input Validation — reject bad inputs cheaply, first")
    print("=" * 60)

    test_inputs = [
        "How do I make pasta from scratch?",                       # valid
        "",                                                         # too short
        "hi",                                                       # too short
        "My email is chef@example.com, what can I cook tonight?",  # PII (redact)
        "What's the best stock to buy on the market right now?",   # off-topic
        "Call me at 555-123-4567 for the recipe",                  # PII phone
    ]

    for text in test_inputs:
        print(f"\n  Input: {text!r}")
        result = validate_input(text)
        if result["valid"]:
            print(f"    VALID ✓")
            if result["pii_found"]:
                print(f"    PII detected & redacted: {result['pii_found']}")
                print(f"    Sent to LLM as: {result['cleaned_input']!r}")
        else:
            print(f"    REJECTED at '{result['stage']}': {result['reason']}")

    print("\n  Order matters: run FREE checks (length, PII regex) before the")
    print("  LLM on-topic check — reject junk before paying for a call.")


if __name__ == "__main__":
    main()
