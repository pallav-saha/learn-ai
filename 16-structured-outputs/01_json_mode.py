"""
01 - JSON Mode: get structured JSON instead of free text

THE PROBLEM with free text:
    Ask "extract the name and age" and you might get:
      "The name is Alice and she's 30."
      "Alice (30)"
      "Name: Alice, Age: 30 years old"
    Every response is worded differently → impossible to parse reliably in code.

THE FIX — JSON mode:
    response_format={"type": "json_object"} forces the model to return valid JSON.
    You describe the shape you want in the prompt, and get back parseable data.

Run:
    cd 16-structured-outputs && ../.venv/bin/python3 01_json_mode.py
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# WITHOUT JSON mode — free text (hard to use)
# ============================================================

def without_json_mode(text: str):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Extract the person's name and age from: {text}"}],
        temperature=0,
    )
    return response.choices[0].message.content


# ============================================================
# WITH JSON mode — structured, parseable
# ============================================================

def with_json_mode(text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                # Describe the exact JSON shape you want
                "content": (
                    f"Extract the person's name and age from this text: {text}\n\n"
                    'Respond ONLY as JSON: {"name": "<string>", "age": <number>}'
                ),
            }
        ],
        temperature=0,
        response_format={"type": "json_object"},  # ← forces valid JSON output
    )
    # Guaranteed to be valid JSON → parse it directly into a dict
    return json.loads(response.choices[0].message.content)


# ============================================================
# A more useful example — classification into structured fields
# ============================================================

def classify_support_ticket(ticket: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify this support ticket:\n{ticket}\n\n"
                    'Respond ONLY as JSON: '
                    '{"category": "<billing|technical|account|other>", '
                    '"priority": "<low|medium|high>", '
                    '"summary": "<one sentence>"}'
                ),
            }
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  JSON Mode — structured output vs free text")
    print("=" * 60)

    sample = "Hi, I'm Alice and I just turned 30 last week."

    # Without JSON mode — unpredictable text
    print("\n  [1] WITHOUT JSON mode (free text — hard to use):")
    raw = without_json_mode(sample)
    print(f"    Got: {raw!r}")
    print("    ↑ Your code would have to parse this string somehow. Fragile.")

    # With JSON mode — clean dict
    print("\n  [2] WITH JSON mode (structured — ready to use):")
    data = with_json_mode(sample)
    print(f"    Got: {data}")
    print(f"    Now use it directly: data['name'] = {data['name']!r}, data['age'] = {data['age']}")

    # Real-world classification
    print("\n  [3] Classifying support tickets into structured fields:")
    tickets = [
        "My credit card was charged twice for the same order!",
        "The app crashes every time I click the export button.",
        "How do I change my email address?",
    ]
    for t in tickets:
        result = classify_support_ticket(t)
        print(f"\n    Ticket: {t}")
        print(f"      category={result['category']} | priority={result['priority']}")
        print(f"      summary: {result['summary']}")

    print("\n  JSON mode turns the LLM into a reliable data extractor —")
    print("  the output plugs straight into your code, no fragile parsing.")


if __name__ == "__main__":
    main()
