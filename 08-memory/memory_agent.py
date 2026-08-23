"""
Memory Agent — An agent that remembers across conversations

Demonstrates 3 types of memory:
1. SHORT-TERM: Conversation history within a session
2. LONG-TERM: Facts saved to a file, persists between runs
3. SEMANTIC: Searchable past conversations using embeddings + ChromaDB

Run: python3 memory_agent.py
Run it multiple times — it remembers you!
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-120b"

MEMORY_FILE = "./agent_memory.json"


# ============================================================
# MEMORY TYPE 1: Short-Term (Conversation History)
# ============================================================
# This is what ChatGPT does — keep all messages in a list
# and send them with every request.

class ShortTermMemory:
    """
    Keeps the conversation history in a list.
    The model "remembers" by re-reading all previous messages.
    
    Problem: Context window has a limit (131K tokens).
    If conversation gets too long, old messages must be dropped.
    """

    def __init__(self, max_messages: int = 20):
        self.messages = []
        self.max_messages = max_messages

    def add(self, role: str, content: str):
        """Add a message to history."""
        self.messages.append({"role": role, "content": content})
        # Keep only the last N messages to avoid hitting token limits
        if len(self.messages) > self.max_messages:
            # Keep system prompt (first) + latest messages
            self.messages = self.messages[:1] + self.messages[-(self.max_messages - 1):]

    def get_messages(self) -> list:
        return self.messages

    def clear(self):
        self.messages = []


# ============================================================
# MEMORY TYPE 2: Long-Term (Persistent Facts)
# ============================================================
# Save important facts to a JSON file on disk.
# These survive between runs — the agent remembers you next time.

class LongTermMemory:
    """
    Stores facts as key-value pairs in a JSON file.
    Persists between runs — the agent remembers you tomorrow.
    
    Examples:
        "user_name" → "Pallab"
        "preferences" → "prefers Python, learning AI"
        "last_topic" → "multi-agent systems"
    """

    def __init__(self, filepath: str = MEMORY_FILE):
        self.filepath = filepath
        self.facts = self._load()

    def _load(self) -> dict:
        """Load facts from disk."""
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Save facts to disk."""
        with open(self.filepath, "w") as f:
            json.dump(self.facts, f, indent=2)

    def remember(self, key: str, value: str):
        """Store a fact."""
        self.facts[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        self._save()
        print(f"   💾 Remembered: {key} = {value}")

    def recall(self, key: str) -> str | None:
        """Recall a fact."""
        fact = self.facts.get(key)
        return fact["value"] if fact else None

    def get_all_facts(self) -> str:
        """Get all facts as a string for the system prompt."""
        if not self.facts:
            return "No stored facts about this user yet."
        lines = []
        for key, data in self.facts.items():
            lines.append(f"- {key}: {data['value']}")
        return "\n".join(lines)

    def clear(self):
        """Clear all memories."""
        self.facts = {}
        self._save()


# ============================================================
# MEMORY TYPE 3: Semantic Memory (Searchable Past Conversations)
# ============================================================
# Store past conversations in ChromaDB with embeddings.
# Search past conversations by meaning — "What did we discuss
# about Python?" finds relevant past exchanges.

class SemanticMemory:
    """
    Stores conversation exchanges in ChromaDB.
    Can search past conversations by meaning.
    
    "What did we talk about last time?" → searches all past exchanges
    and returns relevant ones.
    """

    def __init__(self):
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self.client = chromadb.PersistentClient(path="./memory_chromadb")
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.collection = self.client.get_or_create_collection(
                name="conversations",
                embedding_function=embedding_fn,
            )
            self.available = True
        except ImportError:
            self.available = False
            print("   ⚠️  ChromaDB not available. Semantic memory disabled.")

    def store_exchange(self, user_msg: str, assistant_msg: str):
        """Store a conversation exchange for future recall."""
        if not self.available:
            return

        exchange = f"User asked: {user_msg}\nAssistant answered: {assistant_msg[:200]}"
        exchange_id = f"exchange_{self.collection.count()}"

        self.collection.add(
            documents=[exchange],
            ids=[exchange_id],
            metadatas=[{"timestamp": datetime.now().isoformat()}],
        )

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """Search past conversations by meaning."""
        if not self.available or self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count()),
        )

        return results["documents"][0] if results["documents"] else []

    def count(self) -> int:
        return self.collection.count() if self.available else 0


# ============================================================
# THE MEMORY AGENT — Combines all 3 memory types
# ============================================================

class MemoryAgent:
    """
    An agent with 3 types of memory:
    - Short-term: remembers current conversation
    - Long-term: remembers facts across sessions (name, preferences)
    - Semantic: can search past conversations by meaning
    """

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.semantic = SemanticMemory()

        # System prompt includes long-term facts
        self._update_system_prompt()

    def _update_system_prompt(self):
        """Build system prompt with long-term memory included."""
        facts = self.long_term.get_all_facts()
        past_count = self.semantic.count()

        system_prompt = f"""You are a helpful AI assistant with memory. You remember things about the user.

THINGS YOU KNOW ABOUT THIS USER:
{facts}

PAST CONVERSATIONS: {past_count} exchanges stored.

INSTRUCTIONS:
- If the user tells you their name, preferences, or any personal info, say "I'll remember that."
- Be conversational and reference past context when relevant.
- If asked about past conversations, you can search your memory.
- Be concise and helpful."""

        # Set or update system prompt
        if self.short_term.messages and self.short_term.messages[0]["role"] == "system":
            self.short_term.messages[0] = {"role": "system", "content": system_prompt}
        else:
            self.short_term.messages.insert(0, {"role": "system", "content": system_prompt})

    @retry_on_failure(max_retries=3, delay=2.0)
    def _call_llm(self, messages: list) -> str:
        """Call the LLM."""
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _extract_facts(self, user_msg: str, assistant_msg: str):
        """
        Extract memorable facts from the conversation.
        Simple heuristic — in production, you'd use an LLM to extract.
        """
        msg_lower = user_msg.lower()

        # Detect name
        if "my name is" in msg_lower or "i'm " in msg_lower or "i am " in msg_lower:
            # Try to extract name (simple approach)
            for phrase in ["my name is ", "i'm ", "i am "]:
                if phrase in msg_lower:
                    name = user_msg[msg_lower.index(phrase) + len(phrase):].split(".")[0].split(",")[0].strip()
                    if name and len(name) < 30:
                        self.long_term.remember("user_name", name)
                        break

        # Detect preferences
        if "i like" in msg_lower or "i prefer" in msg_lower or "i love" in msg_lower:
            self.long_term.remember("preferences", user_msg)

        # Detect what they're learning
        if "learning" in msg_lower or "studying" in msg_lower or "teach me" in msg_lower:
            self.long_term.remember("learning_topic", user_msg)

        # Always remember last interaction time
        self.long_term.remember("last_interaction", datetime.now().strftime("%Y-%m-%d %H:%M"))

    def chat(self, user_message: str) -> str:
        """Main chat method — uses all 3 memory types."""

        # Check if user is asking about past conversations
        if any(phrase in user_message.lower() for phrase in
               ["last time", "remember when", "we discussed", "we talked about", "do you remember"]):
            past = self.semantic.search(user_message)
            if past:
                # Add past context to the message
                past_context = "\n".join(past[:2])
                user_message += f"\n\n[CONTEXT FROM PAST CONVERSATIONS:\n{past_context}]"

        # Add user message to short-term memory
        self.short_term.add("user", user_message)

        # Call LLM with full conversation history
        response = self._call_llm(self.short_term.get_messages())

        # Add assistant response to short-term memory
        self.short_term.add("assistant", response)

        # Store in semantic memory for future search
        self.semantic.store_exchange(user_message, response)

        # Extract and save any facts mentioned
        self._extract_facts(user_message, response)

        # Update system prompt with new facts
        self._update_system_prompt()

        return response


# ============================================================
# INTERACTIVE DEMO
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  🧠 MEMORY AGENT — Remembers across conversations!")
    print("=" * 60)

    agent = MemoryAgent()

    # Show what the agent already knows
    facts = agent.long_term.get_all_facts()
    past_count = agent.semantic.count()

    if facts != "No stored facts about this user yet.":
        print(f"\n   📋 I remember these things about you:")
        print(f"   {facts}")
    else:
        print(f"\n   📋 This is our first conversation! I don't know anything about you yet.")

    if past_count > 0:
        print(f"   📚 I have {past_count} past conversation exchanges stored.")

    print(f"""
   Try these:
   • "My name is Pallab"  → I'll remember your name
   • "I like Python and AI" → I'll remember your preferences
   • "What's my name?" → I'll recall from memory
   • "What did we talk about?" → I'll search past conversations

   Run this script again later — I'll still remember you!

   Commands:
   • 'quit' → exit
   • 'clear' → erase all memory
   • 'memory' → show what I remember
""")

    print("-" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye! I'll remember this conversation.")
            break
        if user_input.lower() == "clear":
            agent.long_term.clear()
            print("   🗑️  All memory cleared!")
            continue
        if user_input.lower() == "memory":
            print(f"\n   📋 Long-term memory:")
            print(f"   {agent.long_term.get_all_facts()}")
            print(f"   📚 Semantic memory: {agent.semantic.count()} exchanges\n")
            continue

        response = agent.chat(user_input)
        print(f"\nAgent: {response}\n")
