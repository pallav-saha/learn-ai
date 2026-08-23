"""
FastAPI API powered by Groq LLM

Three endpoints:
1. POST /chat        - Send a message, get a response
2. POST /summarize   - Send text, get a summary
3. POST /code        - Describe what you want, get Python code

Run: python3 app.py
Then visit http://localhost:8000/docs for interactive API docs (free with FastAPI!)
"""

import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from openai import AsyncOpenAI
from utils import retry_on_failure

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(
    title="Groq LLM API",
    description="A simple API powered by Groq's free LLM",
)

# AsyncOpenAI for non-blocking API calls
client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

MODEL = "openai/gpt-oss-20b"


# ============================================================
# Request Models (FastAPI validates these automatically!)
# ============================================================

class ChatRequest(BaseModel):
    message: str

class SummarizeRequest(BaseModel):
    text: str
    length: str = "short"  # default value = optional field

class CodeRequest(BaseModel):
    description: str


# ============================================================
# Helper
# ============================================================

@retry_on_failure(max_retries=3, delay=1.0)
async def ask_llm(system_prompt: str, user_message: str) -> str:
    """Helper to call Groq LLM with a system prompt and user message."""
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


# ============================================================
# ENDPOINT 1: Chat - General conversation
# ============================================================
@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Send a message, get a response.

    FastAPI automatically validates that "message" exists.
    No manual if/else checks needed!
    """
    reply = await ask_llm(
        system_prompt="You are a helpful assistant. Be concise and clear.",
        user_message=req.message,
    )
    return {"reply": reply}


# ============================================================
# ENDPOINT 2: Summarize - Condense long text
# ============================================================
@app.post("/summarize")
async def summarize(req: SummarizeRequest):
    """
    Send text, get a summary.
    Length can be "short", "medium", or "long".
    """
    length_instructions = {
        "short": "Summarize in 1-2 sentences.",
        "medium": "Summarize in a short paragraph (3-4 sentences).",
        "long": "Summarize in detail, keeping all key points.",
    }

    reply = await ask_llm(
        system_prompt=f"You are a summarization expert. {length_instructions.get(req.length, length_instructions['short'])}",
        user_message=f"Summarize this:\n\n{req.text}",
    )
    return {"summary": reply}


# ============================================================
# ENDPOINT 3: Code - Generate Python code
# ============================================================
@app.post("/code")
async def generate_code(req: CodeRequest):
    """
    Describe what you want, get Python code back.
    """
    reply = await ask_llm(
        system_prompt=(
            "You are a Python code generator. "
            "Return ONLY a JSON object with two keys: "
            '"code" (the Python code as a string) and '
            '"explanation" (a one-sentence explanation). '
            "No markdown, no extra text."
        ),
        user_message=req.description,
    )

    # Try to parse as JSON, fallback to raw text
    try:
        result = json.loads(reply)
    except json.JSONDecodeError:
        result = {"code": reply, "explanation": "Generated code above."}

    return result


# ============================================================
# Home page
# ============================================================
@app.get("/")
async def home():
    return {
        "name": "Groq LLM API (FastAPI)",
        "docs": "Visit /docs for interactive API documentation",
        "endpoints": {
            "POST /chat": {"body": {"message": "your question"}},
            "POST /summarize": {"body": {"text": "long text...", "length": "short|medium|long"}},
            "POST /code": {"body": {"description": "what the code should do"}},
        },
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Groq LLM API on http://localhost:8000")
    print("📄 Interactive docs at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
