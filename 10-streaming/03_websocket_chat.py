"""
WebSocket Streaming Chat — Real-time bidirectional chat with LLM

This is the full app: a ChatGPT-like experience where tokens stream in real-time.

Why WebSocket over SSE here?
- User can send a new message while previous stream is still going
- Server can push typing indicators, errors, etc. anytime
- Single persistent connection (no reconnecting per message)
- Better for a proper chat interface

Run:
    cd 10-streaming && ../.venv/bin/python3 03_websocket_chat.py

Then visit: http://localhost:8000

Architecture:
    Browser ←WebSocket→ FastAPI ←async stream→ Groq LLM

Message protocol (JSON over WebSocket):
    Client → Server:  {"type": "message", "content": "Hello"}
    Client → Server:  {"type": "stop"}  (cancel generation)
    Server → Client:  {"type": "token", "content": "Hello"}  (streaming token)
    Server → Client:  {"type": "done"}  (generation complete)
    Server → Client:  {"type": "error", "content": "..."}
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="WebSocket Streaming Chat", version="1.0.0")

# Serve static files (the chat UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
# Tell FastAPI: "Any URL starting with /static/ should serve files from the static/ folder."
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# LLM client
llm_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL = "openai/gpt-oss-20b"


# ============================================================
# CONVERSATION MEMORY (per connection)
# ============================================================

class Conversation:
    """Manages chat history for one WebSocket connection."""
    
    def __init__(self):
        self.messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful, concise assistant. "
                    "Use markdown formatting for code blocks and lists. "
                    "Keep answers focused and practical."
                ),
            }
        ]
        self.is_generating = False  # Track if we're mid-generation
    
    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
    
    def get_messages(self, max_history: int = 20) -> list[dict]:
        """Return system prompt + last N messages."""
        # Always include system prompt + recent history
        system = self.messages[:1]
        history = self.messages[1:][-max_history:]
        return system + history


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================

# When someone connects to ws://localhost:8000/ws/chat, run this function
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Main WebSocket endpoint for streaming chat.
    
    Flow:
    1. Client connects
    2. Client sends {"type": "message", "content": "..."}
    3. Server streams back {"type": "token", "content": "..."} for each token
    4. Server sends {"type": "done"} when generation is complete
    5. Repeat from step 2
    """
    # Accept the connection — like picking up the phone
    await websocket.accept()

    # Create fresh chat history for this user (each connection gets its own)
    conversation = Conversation()
    
    try:
        # Infinite loop: keep listening for messages until user disconnects
        while True:
            # Wait for the browser to send something (pauses here without blocking others)
            # raw = JSON string like '{"type": "message", "content": "Hello"}'
            raw = await websocket.receive_text()

            # Parse JSON string → Python dictionary
            data = json.loads(raw)
            
            # Check what the client wants: "message", "stop", or "clear"
            if data["type"] == "message":
                # Get the message text, skip if empty
                user_message = data["content"].strip()
                if not user_message:
                    continue
                
                # Save user's message to conversation history
                conversation.add_user_message(user_message)
                # Set flag so we can check if user clicks "Stop" later
                conversation.is_generating = True
                
                # Accumulator: collect all tokens to save full response to history later
                full_response = ""
                
                try:
                    # Call the LLM with streaming ON
                    # Sends conversation history to Groq, gets back a stream (tap that drips tokens)
                    stream = await llm_client.chat.completions.create(
                        model=MODEL,
                        messages=conversation.get_messages(),
                        temperature=0.7,
                        max_tokens=1024,
                        stream=True,
                    )
                    
                    # Loop through tokens as they arrive from the LLM, one at a time
                    async for chunk in stream:
                        # Check if user clicked "Stop" — if so, break out of the loop
                        if not conversation.is_generating:
                            break
                        
                        # Extract the token text from the chunk
                        # delta.content = just the new token (None for first/last chunks)
                        content = chunk.choices[0].delta.content
                        if content:
                            # Add to accumulator (to save complete answer later)
                            full_response += content
                            # Send this token to the browser IMMEDIATELY
                            # Browser appends it to the screen = streaming effect
                            await websocket.send_json({
                                "type": "token",
                                "content": content,
                            })
                    
                    # All tokens sent — save complete answer to history
                    # So the LLM remembers what it said on the next question
                    if full_response:
                        conversation.add_assistant_message(full_response)
                    
                    # Tell browser: "I'm finished" — removes cursor, re-enables input
                    await websocket.send_json({"type": "done"})
                
                except Exception as e:
                    # If LLM fails, tell the browser (show error instead of crashing)
                    await websocket.send_json({
                        "type": "error",
                        "content": f"LLM error: {str(e)}",
                    })
                
                finally:
                    # Always reset the flag — whether succeeded, failed, or stopped
                    conversation.is_generating = False
            
            elif data["type"] == "stop":
                # User clicked "Stop" — set flag to False
                # The async for loop above checks this flag and breaks
                conversation.is_generating = False
            
            elif data["type"] == "clear":
                # User clicked "Clear Chat" — reset conversation history
                conversation.__init__()
                await websocket.send_json({
                    "type": "cleared",
                    "content": "Conversation cleared.",
                })
    
    except WebSocketDisconnect:
        # User closed the tab or navigated away — clean up silently
        pass
    except Exception as e:
        # Any other crash — try to tell the browser, if even that fails, give up
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}",
            })
        except:
            pass


# ============================================================
# SERVE THE UI
# ============================================================

@app.get("/")
async def home():
    """Serve the chat UI."""
    html_path = os.path.join(static_dir, "index.html")
    with open(html_path, "r") as f:
        return HTMLResponse(f.read())


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  WebSocket Streaming Chat")
    print("=" * 50)
    print()
    print("  UI:   http://localhost:8000")
    print("  WS:   ws://localhost:8000/ws/chat")
    print("  Docs: http://localhost:8000/docs")
    print()
    print("  Open the UI and start chatting!")
    print("  Tokens will appear in real-time.")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
