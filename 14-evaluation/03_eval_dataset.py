"""
03 - Evaluation Dataset (like unit tests for your LLM app)

An eval dataset is a FIXED set of test cases. You run your system against ALL of them
and get a score. When you change a prompt or model, you re-run and compare:
"did the score go up or down?" — objective, repeatable, catches regressions.

This file:
  1. Defines a test dataset (questions + reference answers)
  2. Runs the "app under test" (a simple LLM Q&A) on each
  3. Grades each answer with an LLM judge
  4. Reports a pass rate + saves results to JSON

Run:
    cd 14-evaluation && ../.venv/bin/python3 03_eval_dataset.py
"""

import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"

# Score >= this counts as a "pass"
PASS_THRESHOLD = 4


# ============================================================
# THE EVAL DATASET — your test cases (the "ground truth")
# ============================================================
# In a real project this lives in a JSON/CSV file and grows over time.
# Each case: the input question + the expected reference answer.

EVAL_DATASET = [
    {"id": "geo-1", "question": "What is the capital of Japan?", "reference": "Tokyo"},
    {"id": "geo-2", "question": "What is the largest ocean?", "reference": "The Pacific Ocean"},
    {"id": "math-1", "question": "What is 15 multiplied by 4?", "reference": "60"},
    {"id": "py-1", "question": "What keyword defines a function in Python?", "reference": "The 'def' keyword"},
    {"id": "py-2", "question": "What does the len() function do in Python?", "reference": "It returns the number of items in an object (like a list or string)."},
    {"id": "sci-1", "question": "What gas do plants absorb from the air?", "reference": "Carbon dioxide (CO2)"},
]


# ============================================================
# THE APP UNDER TEST — the thing we're evaluating
# ============================================================

def run_app(question: str) -> str:
    """The system being evaluated — here, a simple LLM Q&A. Swap in your real app."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Answer concisely in one sentence."},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


# ============================================================
# THE JUDGE — grades each answer (from file 01)
# ============================================================

def judge(question: str, reference: str, answer: str) -> dict:
    prompt = f"""Score how well the ANSWER matches the REFERENCE for the QUESTION (1-5).
5 = fully correct, 1 = wrong.

QUESTION: {question}
REFERENCE: {reference}
ANSWER: {answer}

Respond ONLY as JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# THE EVAL RUNNER — run app + judge on every test case
# ============================================================

def run_evaluation():
    print("=" * 60)
    print(f"  Running evaluation on {len(EVAL_DATASET)} test cases")
    print("=" * 60)

    results = []
    passed = 0
    total_score = 0
    start = time.time()

    for case in EVAL_DATASET:
        # 1. Run the app
        answer = run_app(case["question"])
        # 2. Grade it
        verdict = judge(case["question"], case["reference"], answer)
        score = verdict["score"]
        total_score += score
        is_pass = score >= PASS_THRESHOLD
        if is_pass:
            passed += 1

        status = "PASS" if is_pass else "FAIL"
        print(f"\n  [{status}] {case['id']}: {case['question']}")
        print(f"    Expected: {case['reference']}")
        print(f"    Got:      {answer}")
        print(f"    Score:    {score}/5 — {verdict['reasoning']}")

        results.append({
            "id": case["id"],
            "question": case["question"],
            "reference": case["reference"],
            "answer": answer,
            "score": score,
            "passed": is_pass,
        })

    elapsed = time.time() - start

    # ============================================================
    # REPORT
    # ============================================================
    pass_rate = passed / len(EVAL_DATASET) * 100
    avg_score = total_score / len(EVAL_DATASET)

    print(f"\n  {'=' * 56}")
    print(f"  RESULTS")
    print(f"  {'=' * 56}")
    print(f"  Pass rate:     {passed}/{len(EVAL_DATASET)} ({pass_rate:.0f}%)")
    print(f"  Average score: {avg_score:.2f}/5")
    print(f"  Time:          {elapsed:.1f}s")

    # Save results (so you can compare across runs / prompt changes)
    out_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "pass_rate": pass_rate,
            "average_score": avg_score,
            "results": results,
        }, f, indent=2)
    print(f"\n  Saved detailed results to eval_results.json")
    print("  Change your prompt/model, re-run, and compare the pass rate + avg score.")
    print("  This is how you know if a change made your app BETTER or WORSE.")


if __name__ == "__main__":
    run_evaluation()
