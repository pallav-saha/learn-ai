"""
04 - Agent with Tools (the full function-calling loop)

File 03 showed ONE tool call. A real agent runs a LOOP:
    think → call a tool → observe the result → think again → ... → final answer

This is the heart of every AI agent. Function calling makes it reliable because the
LLM returns structured tool calls (not text we have to parse). The loop can chain
MULTIPLE tools to answer one question.

Run:
    cd 16-structured-outputs && ../.venv/bin/python3 04_agent_with_tools.py
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
# THE TOOLS (real functions)
# ============================================================

def get_weather(city: str) -> str:
    fake = {"Tokyo": "18°C, cloudy", "Paris": "12°C, rainy",
            "Cairo": "33°C, sunny", "London": "10°C, foggy"}
    return fake.get(city, f"Weather unavailable for {city}")


def calculate(expression: str) -> str:
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"


def convert_temperature(celsius: float) -> str:
    return f"{celsius * 9/5 + 32}°F"


AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate": calculate,
    "convert_temperature": convert_temperature,
}

TOOLS = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city (returns temp in Celsius)",
        "parameters": {"type": "object",
                       "properties": {"city": {"type": "string"}},
                       "required": ["city"]}}},
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate a math expression like '15 * 4'",
        "parameters": {"type": "object",
                       "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]}}},
    {"type": "function", "function": {
        "name": "convert_temperature",
        "description": "Convert a temperature from Celsius to Fahrenheit",
        "parameters": {"type": "object",
                       "properties": {"celsius": {"type": "number"}},
                       "required": ["celsius"]}}},
]


# ============================================================
# THE AGENT LOOP
# ============================================================

def run_agent(user_message: str, max_steps: int = 5):
    """
    Run the think → act → observe loop until the LLM gives a final answer
    (or we hit max_steps as a safety limit).
    """
    print(f"\n  {'=' * 56}")
    print(f"  User: {user_message}")
    print(f"  {'=' * 56}")

    # The conversation history grows as the agent works
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed. "
                                       "You can call multiple tools in sequence to answer."},
        {"role": "user", "content": user_message},
    ]

    for step in range(1, max_steps + 1):
        # 1. THINK — ask the LLM what to do next
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message

        # 2. Did it call a tool, or give a final answer?
        if not message.tool_calls:
            # FINAL ANSWER — no more tools needed. Done.
            print(f"\n  [Step {step}] Final answer:")
            print(f"    {message.content}")
            return message.content

        # 3. ACT — the LLM wants to call one or more tools
        # We must append the assistant's tool-call message to history first
        messages.append(message)

        for tc in message.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"\n  [Step {step}] Tool call: {name}({args})")

            # Run the real function
            result = AVAILABLE_FUNCTIONS[name](**args)
            print(f"           Result: {result}")

            # 4. OBSERVE — feed the result back so the LLM can use it
            # (the tool_call_id links this result to the specific call)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })
        # loop back → the LLM now sees the tool results and decides the next step

    return "  (Reached max steps without a final answer)"


# ============================================================
# DEMO
# ============================================================

def main():
    print("=" * 60)
    print("  Agent with Tools — the full think→act→observe loop")
    print("=" * 60)

    # Simple: one tool
    run_agent("What's the weather in Tokyo?")

    # Multi-step: needs TWO tools chained
    # (get weather in Celsius → convert to Fahrenheit)
    run_agent("What's the weather in Cairo, and what is that temperature in Fahrenheit?")

    # Multi-step math
    run_agent("If it's 18 degrees in Tokyo, what is that in Fahrenheit, "
              "and then multiply that number by 2?")

    print("\n  " + "=" * 56)
    print("  This loop (think → call tool → observe → repeat) is how EVERY")
    print("  agent works: ChatGPT plugins, coding agents, Kiro itself.")
    print("  Function calling makes each step reliable (structured, not parsed).")


if __name__ == "__main__":
    main()
