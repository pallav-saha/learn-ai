"""
03 - Function Calling (a.k.a. Tool Calling)

In module 03, you parsed the LLM's TEXT to guess which tool it wanted (fragile).
Function calling is the modern, reliable way: you DESCRIBE your functions to the LLM,
and it responds with a structured "call this function with these arguments" object —
no text parsing needed.

The flow:
    1. Describe your tools (name + parameters as a JSON schema)
    2. LLM responds with tool_calls: [{name, arguments}]  (structured, validated JSON)
    3. YOUR code runs the real function with those arguments
    4. Feed the result back → LLM gives a final answer

Run:
    cd 16-structured-outputs && ../.venv/bin/python3 03_function_calling.py
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
# STEP 1: THE ACTUAL FUNCTIONS (your real code)
# ============================================================
# These are normal Python functions. The LLM never runs them —
# it only asks YOU to run them by name with arguments.

def get_weather(city: str) -> str:
    # Pretend this calls a real weather API
    fake = {"Tokyo": "18°C, cloudy", "Paris": "12°C, rainy", "Cairo": "33°C, sunny"}
    return fake.get(city, f"Weather data unavailable for {city}")


def calculate(expression: str) -> str:
    # A simple calculator (in real code, validate/sandbox this!)
    try:
        # eval("__import__('os').system('rm -rf /')")   # deletes files!
        # eval("open('/etc/passwd').read()")            # reads secret files!

        # eval will run ANY Python code, not just math. Since the expression comes from the LLM (untrusted), a malicious or hallucinated expression could do real damage.
        # By passing {"__builtins__": {}}, you strip out the dangerous functions:

        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"


# Map tool names → the real functions, so we can dispatch by name
AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate": calculate,
}


# ============================================================
# STEP 2: DESCRIBE THE TOOLS TO THE LLM (schemas)
# ============================================================
# This tells the LLM what tools exist, what they do, and what
# arguments they take. The LLM uses this to decide which to call.

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The city name"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression like '15 * 4 + 2'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The math expression"},
                },
                "required": ["expression"],
            },
        },
    },
]


# ============================================================
# STEP 3: THE CALL — let the LLM decide which tool to use
# ============================================================

def demo_single_tool_call(user_message: str):
    print(f"\n  User: {user_message}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": user_message}],
        tools=TOOLS,             # ← tell the LLM what tools exist
        tool_choice="auto",      # ← let it decide whether/which to call
    )

    message = response.choices[0].message

    if message.tool_calls:
        # The LLM chose to call a tool — this is STRUCTURED, not text
        for tc in message.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)  # already valid JSON
            print(f"    LLM wants to call: {name}({args})")

            # STEP 4: WE run the real function
            result = AVAILABLE_FUNCTIONS[name](**args)
            print(f"    Function result: {result}")
    else:
        # No tool needed — the LLM just answered directly
        print(f"    LLM answered directly: {message.content}")


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  Function Calling — LLM picks tools with structured args")
    print("=" * 60)

    # The LLM decides which tool fits each request
    demo_single_tool_call("What's the weather in Tokyo?")      # → get_weather
    demo_single_tool_call("What is 15 times 4 plus 100?")      # → calculate
    demo_single_tool_call("What's the weather in Paris?")      # → get_weather
    demo_single_tool_call("Who painted the Mona Lisa?")        # → no tool, direct answer

    print("\n  Key point: the LLM returned a STRUCTURED tool_call")
    print("  (name + JSON arguments), not text we had to parse.")
    print("  It chose the RIGHT tool for each request automatically.")
    print("\n  Next file (04) closes the loop: feed the result back so the")
    print("  LLM can use it to produce a final answer (a real agent).")


if __name__ == "__main__":
    main()
