"""
Memory Step 1: Short-Term Memory (Conversation History)

This is the SIMPLEST form of memory.
It's just a list of messages that grows as you chat.
The LLM re-reads the entire list every time — so it "remembers"
what you said earlier in the same session.

Problem: When you quit and re-run, everything is forgotten.
(We'll fix that in Step 2)

Run: python3 memory_1_short_term.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-120b"


# ============================================================
# THE ENTIRE "SHORT-TERM MEMORY" IS JUST THIS LIST:
# ============================================================

messages = [
    {"role": "system", "content": "You are a helpful assistant. Be concise."}
]


# ============================================================
# CHAT FUNCTION
# ============================================================

@retry_on_failure(max_retries=3, delay=2.0)
def chat(user_message: str) -> str:
    # 1. Add user message to the list
    messages.append({"role": "user", "content": user_message})

    # 2. Send THE ENTIRE LIST to the LLM
    #    The LLM reads all previous messages — that's how it "remembers"
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,  # ← ALL messages sent every time
    )

    assistant_reply = response.choices[0].message.content

    # 3. Add assistant's reply to the list too
    messages.append({"role": "assistant", "content": assistant_reply})

    return assistant_reply


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🧠 STEP 1: Short-Term Memory")
    print("=" * 60)
    print("""
   This chatbot remembers within a session.
   
   Try:
   1. "My name is Pallab"
   2. "What's my name?"  → It remembers!
   3. "I like Python"
   4. "What do I like?"  → It remembers!
   
   Then quit and re-run → It forgets everything.
   (Step 2 will fix that)
""")
    print("-" * 60)
    print("Type 'quit' to exit, 'history' to see the messages list\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye! (everything is now forgotten)")
            break
        if user_input.lower() == "history":
            print(f"\n📋 Messages list ({len(messages)} items):")
            for i, msg in enumerate(messages):
                role = msg["role"]
                content = msg["content"][:60] + "..." if len(msg["content"]) > 60 else msg["content"]
                print(f"   {i}. [{role}] {content}")
            print()
            continue

        reply = chat(user_input)
        print(f"Bot: {reply}\n")
