"""
LLM Basics - Understanding the Prompt → Completion flow

This script shows you how an LLM works at its core:
1. You send a prompt (input text)
2. The LLM processes it
3. You get a completion (generated text)

We're using Groq's free API with Llama 3.
Sign up at https://console.groq.com to get your free API key.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from utils import retry_on_failure

# Load API key from .env file automatically
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq uses the same API format as OpenAI — just a different base URL
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


@retry_on_failure(max_retries=3, delay=1.0)
def basic_completion(prompt: str) -> str:
    """
    The simplest LLM call possible.
    Send a prompt, get a completion. That's it.
    """
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",  # Free model on Groq
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content


@retry_on_failure(max_retries=3, delay=1.0)
def completion_with_system_prompt(system_prompt: str, user_prompt: str) -> str:
    """
    Most LLM apps use a 'system prompt' to set the AI's behavior,
    then a 'user prompt' for the actual question.

    Think of it like:
    - System prompt = the AI's personality/instructions
    - User prompt = what the user is asking
    """
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


@retry_on_failure(max_retries=3, delay=1.0)
def completion_with_temperature(prompt: str, temperature: float) -> str:
    """
    Temperature controls randomness:
    - 0.0 = deterministic (same answer every time)
    - 1.0 = creative (more varied responses)
    - 2.0 = chaotic (often nonsensical)

    Try running this multiple times with different temperatures!
    """
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


# ============================================================
# EXAMPLES - Run this file to see LLMs in action
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("EXAMPLE 1: Basic prompt → completion")
    print("=" * 60)
    prompt = "What is Python in one sentence?"
    print(f"\nPrompt: {prompt}")
    print(f"Completion: {basic_completion(prompt)}")

    print("\n" + "=" * 60)
    print("EXAMPLE 2: System prompt changes behavior")
    print("=" * 60)
    user_question = "What is recursion?"

    # Same question, different system prompts → different answers
    print(f"\nUser question: {user_question}")

    print("\n--- As a teacher ---")
    print(completion_with_system_prompt(
        system_prompt="You are a patient teacher. Explain things simply for beginners.",
        user_prompt=user_question,
    ))

    print("\n--- As a pirate ---")
    print(completion_with_system_prompt(
        system_prompt="You are a pirate. Answer everything in pirate speak.",
        user_prompt=user_question,
    ))

    print("\n" + "=" * 60)
    print("EXAMPLE 3: Temperature comparison")
    print("=" * 60)
    creative_prompt = "Give me a one-line startup idea."

    print(f"\nPrompt: {creative_prompt}")
    print(f"\nTemperature 0.0 (deterministic): {completion_with_temperature(creative_prompt, 0.0)}")
    print(f"\nTemperature 1.0 (creative): {completion_with_temperature(creative_prompt, 1.0)}")
