"""
02 - RAG Evaluation

RAG has TWO things that can break:
  1. Retrieval  — did it fetch the right context?
  2. Generation — did it use that context correctly (or hallucinate)?

These metrics separate the two so you know WHICH part is broken:

  - FAITHFULNESS      : is the answer grounded in the retrieved context? (catches hallucination)
  - ANSWER RELEVANCE  : does the answer actually address the question?
  - CONTEXT RELEVANCE : was the retrieved context actually useful for the question?

Each is measured with an LLM judge (same idea as file 01, different criteria).

Run:
    cd 14-evaluation && ../.venv/bin/python3 02_rag_evaluation.py
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


def _judge(prompt: str) -> dict:
    """Helper: ask the judge LLM for a JSON score."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ============================================================
# METRIC 1: FAITHFULNESS — is the answer grounded in the context?
# ============================================================

def faithfulness(context: str, answer: str) -> dict:
    """
    Checks: does the answer ONLY contain claims supported by the context?
    A low score means the model HALLUCINATED (made up info not in the context).

    Faithfulness asks: is every claim in the answer actually backed by the retrieved context? The emphasis is on the word ONLY. It's not enough for the answer to be mostly right — every statement it makes has to trace back to something in the context. If the answer adds even one fact that isn't in the context, that's a hallucination, and the score drops.
    Notice what it compares: context vs answer. It does not look at the question. It doesn't care whether the answer is on-topic — only whether the answer stayed within the boundaries of what the context actually said.
    This is the subtle part. Faithfulness isn't asking "is the answer true in the real world?" It's asking "did the model stick to its source material?"
    An answer could be factually true in reality but still score low on faithfulness — if that truth wasn't in the provided context, the model pulled it from its own memory instead of the retrieved documents. In RAG, that's still a failure, because the whole point of RAG is that answers should come from your documents, not the model's imagination. The model is supposed to be grounded, not creative.

    Score 5 = every claim in the answer is supported by the context.
    Score 1 = the answer contains claims not found in the context (made-up info).
    """

    prompt = f"""Judge FAITHFULNESS: does the ANSWER only contain information supported by the CONTEXT?

Score 1-5:
  5 = every claim in the answer is supported by the context
  1 = the answer contains claims NOT found in the context (hallucination)

CONTEXT: {context}

ANSWER: {answer}

Respond ONLY as JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""
    return _judge(prompt)


# ============================================================
# METRIC 2: ANSWER RELEVANCE — does it address the question?
# ============================================================

def answer_relevance(question: str, answer: str) -> dict:
    """Checks: does the answer actually address what was asked?
    Answer relevance asks a simple question: did the answer stay on topic and respond to what was actually asked? It compares the question against the answer — and notice what it does NOT look at: the context. It doesn't care whether the answer is true or grounded. It only cares whether the answer is on point for the question.
    
    So the three metrics form a diagnostic map:
    Faithfulness low → model is hallucinating → fix the generation prompt.
    Context relevance low → retrieval fetched the wrong chunks → fix chunking/embeddings.
    Answer relevance low → model is dodging or drifting off-topic → the answer doesn't serve the user even if everything else is fine.
    """

    prompt = f"""Judge ANSWER RELEVANCE: does the ANSWER directly address the QUESTION?

Score 1-5:
  5 = fully addresses the question
  1 = off-topic or dodges the question

QUESTION: {question}

ANSWER: {answer}

Respond ONLY as JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""
    return _judge(prompt)


# ============================================================
# METRIC 3: CONTEXT RELEVANCE — was retrieval useful?
# ============================================================

def context_relevance(question: str, context: str) -> dict:
    """
    Checks: is the retrieved context actually relevant to the question?
    Low score = your RETRIEVAL is broken (fetching the wrong chunks).

    Context relevance asks: did the retrieval step fetch the right documents in the first place? It compares the question against the context — and crucially, it does NOT look at the answer at all. It's judging the raw material that was pulled from your knowledge base, before the model even writes a response.
    The other two metrics judge the output end (the answer). Context relevance judges the input end — the context that retrieval produced. It's checking the pipeline before generation even happens.

    That's why it only needs the question and the context. The answer is irrelevant here; you're auditing whether your search/embedding step did its job.
    question="What is the return policy?",
    context="Our office is open Monday to Friday, 9am to 5pm. Parking is available in the rear lot.",
    answer="I don't have information about the return policy in the provided context.",
    Run context relevance on this and it scores low, because:

    The question is about the return policy.
    The retrieved context is about office hours and parking — completely unrelated.

    Without context relevance, you'd see the bad answer and might wrongly blame the model's prompt. Context relevance tells you the real culprit was retrieval, not generation.
    Low context relevance → RETRIEVAL is broken (fix chunking/embeddings)
    If context relevance is low, the fix is on the retrieval side, not the prompt:

    Chunking — maybe your documents are split badly (too big, too small, or cutting across topics).
    Embeddings — maybe the embedding model isn't capturing meaning well, so similarity search misses the right chunk.
    Retrieval settings — top-k too low, wrong distance metric, or a query that needs rewriting/hybrid search.
    """
    
    prompt = f"""Judge CONTEXT RELEVANCE: is the CONTEXT useful for answering the QUESTION?

Score 1-5:
  5 = context is highly relevant and sufficient to answer
  1 = context is irrelevant to the question

QUESTION: {question}

CONTEXT: {context}

Respond ONLY as JSON: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""
    return _judge(prompt)


# ============================================================
# DEMO
# ============================================================

def evaluate_rag(question, context, answer):
    """Run all 3 metrics on one RAG example."""
    f = faithfulness(context, answer)
    ar = answer_relevance(question, answer)
    cr = context_relevance(question, context)

    print(f"    Faithfulness    : {f['score']}/5 — {f['reasoning']}")
    print(f"    Answer relevance: {ar['score']}/5 — {ar['reasoning']}")
    print(f"    Context relevance: {cr['score']}/5 — {cr['reasoning']}")
    return f["score"], ar["score"], cr["score"]


def main():
    print("=" * 60)
    print("  RAG Evaluation — faithfulness, relevance, context")
    print("=" * 60)

    # --- Example 1: A GOOD RAG response ---
    print("\n  [1] GOOD response (grounded, relevant, good context):")
    evaluate_rag(
        question="What is the return policy?",
        context="Our return policy allows returns within 30 days of purchase with a receipt. Refunds are processed in 5-7 business days.",
        answer="You can return items within 30 days of purchase if you have a receipt.",
    )

    # --- Example 2: HALLUCINATION (answer invents info not in context) ---
    print("\n  [2] HALLUCINATION (answer adds info NOT in the context):")
    evaluate_rag(
        question="What is the return policy?",
        context="Our return policy allows returns within 30 days of purchase with a receipt.",
        answer="You can return items within 90 days and get free express shipping on all returns.",
    )

    # --- Example 3: BAD RETRIEVAL (context is irrelevant to the question) ---
    print("\n  [3] BAD RETRIEVAL (context doesn't match the question):")
    evaluate_rag(
        question="What is the return policy?",
        context="Our office is open Monday to Friday, 9am to 5pm. Parking is available in the rear lot.",
        answer="I don't have information about the return policy in the provided context.",
    )

    print("\n  " + "=" * 56)
    print("  How to read this:")
    print("    Low faithfulness      → the model is HALLUCINATING (fix the prompt)")
    print("    Low context relevance → RETRIEVAL is broken (fix chunking/embeddings)")
    print("    Low answer relevance  → the model is dodging the question")
    print("  These 3 metrics tell you WHICH part of RAG to fix.")


if __name__ == "__main__":
    main()
