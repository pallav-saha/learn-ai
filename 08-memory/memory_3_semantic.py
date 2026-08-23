"""
Memory Step 3: Semantic Memory (Searchable past conversations)

Problem with Step 2: After 100+ messages, the list is too long 
to send to the LLM (context window limit). You have to trim old 
messages — but then you lose them forever.

Solution: Store old conversations in ChromaDB (vector DB).
Keep only RECENT messages in the active list.
When the user asks about something old, SEARCH ChromaDB and 
inject relevant past context.

This gives you:
- Unlimited history (stored in ChromaDB)
- Short active context (only last 10 messages sent to LLM)
- Smart recall (search past by meaning, not just exact words)

Run: python3 memory_3_semantic.py
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-120b"

MAX_ACTIVE_MESSAGES = 10  # Only keep last 10 messages in active context


# ============================================================
# SEMANTIC MEMORY — ChromaDB stores all past conversations
# ============================================================

print("🧠 Loading memory...")
chroma_client = chromadb.PersistentClient(path="./semantic_memory_db")
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
memory_collection = chroma_client.get_or_create_collection(
    name="chat_memory",
    embedding_function=embedding_fn,
)
print(f"   📚 {memory_collection.count()} past exchanges in memory")


# ============================================================
# ACTIVE MESSAGES — Only recent messages sent to LLM
# ============================================================

messages = [
    {"role": "system", "content": "You are a helpful assistant with memory. Be concise. If past context is provided, use it to answer."}
]


# ============================================================
# STORE an exchange in long-term memory
# ============================================================

def store_in_memory(user_msg: str, bot_reply: str):
    """Save a conversation exchange to ChromaDB for future search."""
    exchange_text = f"User: {user_msg}\nAssistant: {bot_reply}"
    exchange_id = f"msg_{memory_collection.count()}"

    memory_collection.add(
        documents=[exchange_text],
        ids=[exchange_id],
    )


# ============================================================
# SEARCH past conversations by meaning
# ============================================================

def search_memory(query: str, top_k: int = 3) -> list[str]:
    """Search past conversations. Returns relevant past exchanges."""
    if memory_collection.count() == 0:
        return []

    results = memory_collection.query(
        query_texts=[query],
        n_results=min(top_k, memory_collection.count()),
    )

    return results["documents"][0] if results["documents"] else []


# ============================================================
# CHAT FUNCTION — combines active context + semantic search
# ============================================================

@retry_on_failure(max_retries=3, delay=2.0)
def chat(user_message: str) -> str:
    # 1. Search past memory for relevant context
    past_context = search_memory(user_message)

    # 2. Build the user message (optionally with past context)
    full_message = user_message
    if past_context:
        context_text = "\n".join(past_context[:2])  # Top 2 relevant past exchanges
        full_message = f"{user_message}\n\n[Relevant past conversations:\n{context_text}]"

    # 3. Add to active messages
    messages.append({"role": "user", "content": full_message})

    # 4. Trim if too long (keep only last N messages + system prompt)
    if len(messages) > MAX_ACTIVE_MESSAGES + 1:
        messages[1:] = messages[-(MAX_ACTIVE_MESSAGES):]

    # 5. Call LLM
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    bot_reply = response.choices[0].message.content

    # 6. Add reply to active messages
    messages.append({"role": "assistant", "content": bot_reply})

    # 7. Store this exchange in long-term memory (ChromaDB)
    store_in_memory(user_message, bot_reply)

    return bot_reply


# ============================================================
# DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🧠 STEP 3: Semantic Memory (Searchable)")
    print("=" * 60)
    print(f"""
   Active context: Last {MAX_ACTIVE_MESSAGES} messages sent to LLM
   Long-term memory: {memory_collection.count()} past exchanges in ChromaDB
   
   How it works:
   - Only last {MAX_ACTIVE_MESSAGES} messages are sent to the LLM (saves tokens)
   - ALL conversations are stored in ChromaDB forever
   - When you ask something, it searches past conversations
   - Relevant past exchanges are injected as context
   
   Try:
   1. "My name is Pallab and I work at Acme Corp"
   2. "I like building AI agents"
   3. Chat about other things for a while...
   4. "What's my name?" → searches memory, finds it even if
      it's no longer in the last {MAX_ACTIVE_MESSAGES} messages!
   
   Commands:
   • 'quit' → exit
   • 'memory' → show memory stats
   • 'search: <query>' → manually search past conversations
   • 'clear' → erase all memory
""")
    print("-" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print(f"\nGoodbye! {memory_collection.count()} exchanges saved in memory.")
            break
        if user_input.lower() == "memory":
            print(f"\n📋 Active messages: {len(messages) - 1}")
            print(f"📚 Long-term memory: {memory_collection.count()} exchanges in ChromaDB\n")
            continue
        if user_input.lower().startswith("search:"):
            query = user_input[7:].strip()
            results = search_memory(query)
            print(f"\n🔍 Found {len(results)} relevant past exchanges:")
            for r in results:
                print(f"   • {r[:100]}...")
            print()
            continue
        if user_input.lower() == "clear":
            chroma_client.delete_collection("chat_memory")
            memory_collection = chroma_client.get_or_create_collection(
                name="chat_memory", embedding_function=embedding_fn
            )
            messages.clear()
            messages.append({"role": "system", "content": "You are a helpful assistant with memory. Be concise."})
            print("   🗑️ All memory cleared!\n")
            continue

        reply = chat(user_input)
        print(f"Bot: {reply}\n")
