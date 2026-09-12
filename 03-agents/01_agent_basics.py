"""
Agent Basics - Build your first AI agent from scratch

This shows you how agents work under the hood:
- An LLM that can use TOOLS
- A loop that keeps going until the task is done

We build a simple agent that can:
1. Do math (calculator tool)
2. Get the current date/time
3. Look up word definitions (fake dictionary for demo)
4. Search Wikipedia for real-world knowledge

Run: python3 01_agent_basics.py
Make sure GROQ_API_KEY is set.
"""

import os
import json
from datetime import datetime
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


# ============================================================
# STEP 1: Define Tools (things the agent can DO)
# ============================================================

def calculator(expression: str) -> str:
    """Evaluate a math expression and return the result."""
    try:
        result = eval(expression)  # In production, use a safe math parser!
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def get_current_time() -> str:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")


def define_word(word: str) -> str:
    """Look up a word definition (simplified demo dictionary)."""
    definitions = {
        "agent": "A system that can perceive its environment, make decisions, and take actions to achieve goals.",
        "llm": "Large Language Model - a neural network trained on text data that can generate human-like text.",
        "api": "Application Programming Interface - a way for software programs to communicate with each other.",
        "token": "A chunk of text (word or sub-word) that an LLM processes as a single unit.",
        "prompt": "The input text given to an LLM to generate a response.",
    }
    return definitions.get(word.lower(), f"Definition not found for '{word}'. I only know: {', '.join(definitions.keys())}")


def search_wikipedia(query: str) -> str:
    """Search Wikipedia and return a summary of the top result."""
    import wikipediaapi

    wiki = wikipediaapi.Wikipedia(
        user_agent="AgentBasicsDemo/1.0 (learning project)",
        language="en",
    )

    page = wiki.page(query)

    if not page.exists():
        return f"No Wikipedia article found for '{query}'."

    # Return first 500 characters of the summary
    summary = page.summary[:500]
    return f"Wikipedia: {page.title}\n\n{summary}..."


# ============================================================
# STEP 2: Describe tools for the LLM (so it knows what's available)
# ============================================================

# This is the format LLMs understand — a JSON schema for each tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a math expression. Use this for any calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression to evaluate, e.g. '2 + 2' or '(100 / 5) * 3'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time. Use when asked about today's date or current time.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "define_word",
            "description": "Look up the definition of a word related to AI/tech.",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {
                        "type": "string",
                        "description": "The word to define"
                    }
                },
                "required": ["word"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_wikipedia",
            "description": "Search Wikipedia for information about any topic. Use this when the user asks about people, places, events, science, history, or anything you need factual knowledge about.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic to search for on Wikipedia, e.g. 'Python programming language' or 'Albert Einstein'"
                    }
                },
                "required": ["query"]
            }
        }
    },
]

# Map tool names to actual functions
tool_functions = {
    "calculator": lambda args: calculator(args["expression"]),
    "get_current_time": lambda args: get_current_time(),
    "define_word": lambda args: define_word(args["word"]),
    "search_wikipedia": lambda args: search_wikipedia(args["query"]),
}


# ============================================================
# STEP 3: The Agent Loop (this is the magic)
# ============================================================

def run_agent(user_goal: str, max_steps: int = 5):
    """
    The core agent loop:
    1. Send the goal + tools to the LLM
    2. If LLM wants to use a tool → execute it, send result back
    3. If LLM gives a final answer → we're done
    4. Repeat until done or max steps reached
    """
    print(f"\n🎯 Goal: {user_goal}")
    print("-" * 50)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to tools. Use them when needed to answer questions accurately. Think about which tool to use before calling it."
        },
        {"role": "user", "content": user_goal}
    ]

    for step in range(1, max_steps + 1):
        print(f"\n📍 Step {step}:")

        # Ask the LLM what to do
        @retry_on_failure(max_retries=3, delay=1.0)
        def call_llm():
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

        response = call_llm()

        # print(response)
        message = response.choices[0].message
        # print("message -- ", message)

        # Case 1: LLM wants to call tool(s)
        if message.tool_calls:
            # Add the assistant's message (with tool calls) to history
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"   🔧 Using tool: {tool_name}({tool_args})")

                # Execute the tool
                result = tool_functions[tool_name](tool_args)
                print(f"   📋 Result: {result}")

                # Send the result back to the LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        # Case 2: LLM gives a final answer (no tool calls)
        else:
            print(f"   💬 Final answer:")
            print(f"   {message.content}")
            return message.content

    print("\n⚠️  Max steps reached without a final answer.")
    return None


# ============================================================
# INTERACTIVE DEMO
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  🤖 YOUR FIRST AI AGENT")
    print("=" * 60)
    print("""
This agent has 4 tools:
  🧮 calculator       - does math
  🕐 get_time         - knows today's date/time
  📖 define_word      - defines AI/tech terms
  🌐 search_wikipedia - searches Wikipedia for any topic

Try these example goals:
  • "What's 47 * 89 + 12?"
  • "What day is it today?"
  • "Tell me about Elon Musk"
  • "What is the Great Wall of China?"
  • "Search Wikipedia for Python programming and calculate 2**20"
  
The agent will DECIDE which tools to use on its own!
""")

    print("-" * 60)
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("🎯 Your goal: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue
        run_agent(user_input)
        print("\n" + "=" * 60)
