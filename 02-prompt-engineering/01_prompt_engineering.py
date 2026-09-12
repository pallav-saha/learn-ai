"""
Prompt Engineering - See how prompt quality changes output quality

This script demonstrates 6 techniques side-by-side so you can
see the difference between bad and good prompts.

Run: python3 01_prompt_engineering.py
Make sure GROQ_API_KEY is set.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from utils import retry_on_failure

# Load API key from .env file automatically
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-20b"


@retry_on_failure(max_retries=3, delay=1.0)
def ask(prompt: str, system: str = None) -> str:
    """Helper to call the LLM."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


def divider(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


# ============================================================
# TECHNIQUE 1: Be Specific
# ============================================================
def demo_specificity():
    divider("TECHNIQUE 1: Be Specific")

    bad_prompt = "Tell me about Python"
    good_prompt = "Explain Python list comprehensions in 3 sentences for someone who knows basic for loops. Include one example."

    print(f"\n❌ Vague prompt: \"{bad_prompt}\"")
    print(f"\nResponse:\n{ask(bad_prompt)}")

    print(f"\n\n✅ Specific prompt: \"{good_prompt}\"")
    print(f"\nResponse:\n{ask(good_prompt)}")


# ============================================================
# TECHNIQUE 2: Role Prompting
# ============================================================
def demo_roles():
    divider("TECHNIQUE 2: Role Prompting")

    question = "What is an API?"

    print(f"\nSame question: \"{question}\"")

    print("\n--- No role ---")
    print(ask(question))

    print("\n--- Role: Teacher for 5-year-olds ---")
    print(ask(
        question,
        system="You explain things to 5-year-olds using simple words and fun analogies. Keep it to 2-3 sentences."
    ))

    print("\n--- Role: Senior engineer in a code review ---")
    print(ask(
        question,
        system="You are a senior software engineer in a code review. Be technical and precise. Keep it to 2-3 sentences."
    ))


# ============================================================
# TECHNIQUE 3: Few-Shot Examples
# ============================================================
def demo_few_shot():
    divider("TECHNIQUE 3: Few-Shot Examples")

    # Without examples - model has to guess the format
    bad_prompt = "Convert 'The Quick Brown Fox' to a URL slug"

    # With examples - model sees the pattern
    good_prompt = """Convert text to URL slugs. Follow these examples:

"Hello World" → "hello-world"
"My First Blog Post" → "my-first-blog-post"  
"Python 3.12 Release Notes" → "python-312-release-notes"

Now convert: "The Quick Brown Fox Jumps Over"
"""

    print(f"\n❌ No examples:")
    print(f"Prompt: \"{bad_prompt}\"")
    print(f"Response: {ask(bad_prompt)}")

    print(f"\n✅ With examples (few-shot):")
    print(f"Prompt: (shows 3 examples first)")
    print(f"Response: {ask(good_prompt)}")


# ============================================================
# TECHNIQUE 4: Chain of Thought
# ============================================================
def demo_chain_of_thought():
    divider("TECHNIQUE 4: Chain of Thought")

    problem = "A store has 3 shelves. Each shelf has 4 boxes. Each box has 12 items. 25% of all items are defective. How many good items are there?"

    bad_prompt = problem
    good_prompt = f"{problem}\n\nThink step by step."

    print(f"\nProblem: {problem}")

    print("\n❌ Direct (no reasoning):")
    print(ask(bad_prompt))

    print("\n✅ With 'Think step by step':")
    print(ask(good_prompt))


# ============================================================
# TECHNIQUE 5: Output Format Control
# ============================================================
def demo_output_format():
    divider("TECHNIQUE 5: Output Format Control")

    bad_prompt = "Give me some Python web frameworks"

    good_prompt = """List 4 Python web frameworks.
Return as JSON array with fields:
- name: framework name
- use_case: one sentence on when to use it
- difficulty: "beginner", "intermediate", or "advanced"

Return ONLY the JSON, no explanation."""

    print(f"\n❌ No format specified:")
    print(f"Prompt: \"{bad_prompt}\"")
    print(f"Response:\n{ask(bad_prompt)}")

    print(f"\n✅ JSON format specified:")
    print(f"Response:\n{ask(good_prompt)}")


# ============================================================
# TECHNIQUE 6: Constraints
# ============================================================
def demo_constraints():
    divider("TECHNIQUE 6: Constraints")

    bad_prompt = "Explain microservices"

    good_prompt = """Explain microservices.
Rules:
- Exactly 3 bullet points
- Max 15 words per bullet
- No jargon - a non-technical CEO should understand
- Include one real-world analogy"""

    print(f"\n❌ No constraints (will ramble):")
    print(f"Prompt: \"{bad_prompt}\"")
    print(f"Response:\n{ask(bad_prompt)}")

    print(f"\n✅ With constraints (focused):")
    print(f"Response:\n{ask(good_prompt)}")


# ============================================================
# BONUS: The Full Formula
# ============================================================
def demo_full_formula():
    divider("BONUS: The Complete Prompt Formula")

    print("\nFormula: [Role] + [Context] + [Task] + [Format] + [Constraints]\n")

    full_prompt = """I have a list of customer ages: [23, 45, 31, 67, 29, 52, 38, 41, 55, 33]

Write a Python function that:
1. Calculates the average age
2. Finds customers above average
3. Returns a dictionary with keys: average, above_average_count, above_average_ages

Use type hints. Add a docstring. No imports needed."""

    system = "You are a senior Python developer who writes clean, production-ready code. Only return the code, no explanation."

    print(f"System: {system}")
    print(f"\nPrompt: {full_prompt}")
    print(f"\nResponse:\n{ask(full_prompt, system=system)}")


# ============================================================
# RUN ALL DEMOS
# ============================================================
if __name__ == "__main__":
    print("\n🎯 PROMPT ENGINEERING DEMOS")
    print("See how better prompts → better outputs\n")

    demos = [
        ("1", "Specificity", demo_specificity),
        ("2", "Role Prompting", demo_roles),
        ("3", "Few-Shot Examples", demo_few_shot),
        ("4", "Chain of Thought", demo_chain_of_thought),
        ("5", "Output Format", demo_output_format),
        ("6", "Constraints", demo_constraints),
        ("B", "Full Formula", demo_full_formula),
    ]

    print("Which demo to run?")
    for key, name, _ in demos:
        print(f"  {key}) {name}")
    print("  A) Run ALL demos")

    choice = input("\nEnter choice: ").strip().upper()

    if choice == "A":
        for _, _, fn in demos:
            fn()
    else:
        for key, _, fn in demos:
            if key == choice:
                fn()
                break
        else:
            print("Invalid choice. Run the script again.")
