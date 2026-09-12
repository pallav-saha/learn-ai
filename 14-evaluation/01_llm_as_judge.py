"""
01 - LLM as Judge

The core evaluation technique: use a SECOND LLM to grade the output of your main LLM.

Instead of a human reading every answer, you ask a "judge" LLM:
    "Here's a question, a reference answer, and the model's answer.
     Score how correct it is (1-5) and explain why."

This is cheap, fast, and scales to thousands of test cases.

Run:
    cd 14-evaluation && ../.venv/bin/python3 01_llm_as_judge.py
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
# THE JUDGE — grades an answer against a reference
# ============================================================

def judge_answer(question: str, reference: str, answer: str) -> dict:
    """
    Ask the LLM to grade an answer. Returns a score (1-5) + reasoning.

    Key techniques for a reliable judge:
      - Give CLEAR scoring criteria (what does 1 vs 5 mean?)
      - Ask for structured output (JSON) so it's parseable
      - Ask for reasoning (makes the score more reliable + explainable)
      - Use temperature=0 for consistent grading
    """
    judge_prompt = f"""You are an impartial grader. Score how well the ANSWER matches the REFERENCE answer for the given QUESTION.

Scoring scale:
  5 = Fully correct, matches the reference meaning completely
  4 = Mostly correct, minor omissions
  3 = Partially correct, missing important details
  2 = Mostly incorrect, some relevant content
  1 = Completely wrong or irrelevant

QUESTION: {question}

REFERENCE ANSWER: {reference}

MODEL ANSWER: {answer}

Respond ONLY with JSON in this exact format:
{{"score": <1-5>, "reasoning": "<one sentence explaining the score>"}}"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": judge_prompt}],
        temperature=0,  # deterministic grading
        response_format={"type": "json_object"},  # force valid JSON
    )

    return json.loads(response.choices[0].message.content)


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  LLM as Judge — automatic answer grading")
    print("=" * 60)

    # Test cases: question, the "correct" reference, and answers of varying quality
    test_cases = [
        {
            "question": "What is the capital of France?",
            "reference": "Paris",
            "answer": "The capital of France is Paris.",  # correct
        },
        {
            "question": "What is the capital of France?",
            "reference": "Paris",
            "answer": "The capital of France is London.",  # wrong
        },
        {
            "question": "Explain what a Python list is.",
            "reference": "A list is an ordered, mutable collection that can hold items of any type.",
            "answer": "A list stores multiple items in order and you can change it.",  # mostly right
        },
        {
            "question": "What year was Python created?",
            "reference": "Python was created in 1991 by Guido van Rossum.",
            "answer": "Python is a programming language used for many things.",  # dodges the question
        },
    ]

    scores = []
    for i, tc in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {tc['question']}")
        print(f"    Reference: {tc['reference']}")
        print(f"    Answer:    {tc['answer']}")

        result = judge_answer(tc["question"], tc["reference"], tc["answer"])
        scores.append(result["score"])

        print(f"    → SCORE: {result['score']}/5")
        print(f"      Reason: {result['reasoning']}")

    # Aggregate
    avg = sum(scores) / len(scores)
    print(f"\n  {'=' * 56}")
    print(f"  Average score: {avg:.2f}/5 across {len(scores)} tests")
    print(f"  {'=' * 56}")
    print("\n  This is how you grade hundreds of answers automatically.")
    print("  Change your prompt/model, re-run, compare the average → objective measurement.")


if __name__ == "__main__":
    main()
