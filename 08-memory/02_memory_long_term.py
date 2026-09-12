"""
Memory Step 2: Long-Term Memory (Persists between runs)

Building on Step 1 — now we SAVE the conversation to a file.
When you re-run the script, it LOADS the previous conversation.

The LLM never forgets because we load old messages from disk.

Problem: If you chat for hours, the file gets huge and exceeds
the LLM's context window. (We'll fix that in Step 3)

Run: python3 02_memory_long_term.py
Run again → it remembers everything from last time!
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-120b"

HISTORY_FILE = "./chat_history.json"


# ============================================================
# LOAD previous conversation from file (if exists)
# ============================================================

def load_history() -> list:
    """Load chat history from disk. Returns empty list if no history."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    # First time — start with just the system prompt
    return [{"role": "system", "content": "You are a helpful assistant. Be concise."}]


def save_history(messages: list):
    """Save chat history to disk after every message."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(messages, f, indent=2)


# ============================================================
# LOAD HISTORY — This is the magic. Old conversations come back!
# ============================================================

messages = load_history()


# ============================================================
# CHAT FUNCTION (same as Step 1, but saves after each message)
# ============================================================

@retry_on_failure(max_retries=3, delay=2.0)
def chat(user_message: str) -> str:
    # 1. Add user message
    messages.append({"role": "user", "content": user_message})

    # 2. Send all messages to LLM
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    assistant_reply = response.choices[0].message.content

    # 3. Add assistant reply
    messages.append({"role": "assistant", "content": assistant_reply})

    # 4. SAVE TO FILE — this is the only new line vs Step 1!
    save_history(messages)

    return assistant_reply


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🧠 STEP 2: Long-Term Memory (File-based)")
    print("=" * 60)

    msg_count = len(messages) - 1  # exclude system prompt
    if msg_count > 0:
        print(f"\n   📂 Loaded {msg_count} messages from previous sessions!")
        print(f"   I remember our past conversations.")
    else:
        print(f"\n   📂 No previous history. Starting fresh.")

    print("""
   Try:
   1. "My name is Pallab"
   2. "I'm learning AI"
   3. Quit and re-run the script
   4. "What's my name?" → It still remembers!
   
   Commands:
   • 'quit' → exit (memory is saved)
   • 'history' → show message count
   • 'clear' → erase all memory
""")
    print("-" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye! Your conversation is saved.")
            print(f"   (Stored in {HISTORY_FILE})")
            break
        if user_input.lower() == "history":
            print(f"\n📋 {len(messages) - 1} messages stored in {HISTORY_FILE}\n")
            continue
        if user_input.lower() == "clear":
            messages.clear()
            messages.append({"role": "system", "content": "You are a helpful assistant. Be concise."})
            save_history(messages)
            print("   🗑️ All memory cleared!\n")
            continue

        reply = chat(user_input)
        print(f"Bot: {reply}\n")
