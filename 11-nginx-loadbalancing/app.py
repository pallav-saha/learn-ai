"""
Simple FastAPI app for demonstrating Nginx load balancing.

We run MULTIPLE copies of this app on different ports.
Each copy knows its own "name" (from an env variable) so you can SEE
which copy handled each request when Nginx distributes traffic.

Run 3 copies (in 3 separate terminals):
    SERVER_NAME="Server-1" ../.venv/bin/python3 app.py --port 8001
    SERVER_NAME="Server-2" ../.venv/bin/python3 app.py --port 8002
    SERVER_NAME="Server-3" ../.venv/bin/python3 app.py --port 8003

Then Nginx (on port 8080) will spread requests across all 3.
"""

import os
import time
import argparse
from fastapi import FastAPI

app = FastAPI(title="Load Balancing Demo")

# Each copy has a name so we can see which one responds
SERVER_NAME = os.getenv("SERVER_NAME", "Unknown-Server")

# Count how many requests THIS copy has handled
request_count = 0


@app.get("/")
async def home():
    """Returns which server handled this request."""
    global request_count
    request_count += 1
    return {
        "message": "Hello from FastAPI!",
        "handled_by": SERVER_NAME,
        "this_server_request_count": request_count,
    }


@app.get("/slow")
async def slow():
    """A slow endpoint — simulates heavy work (2 seconds)."""
    global request_count
    request_count += 1
    import asyncio
    await asyncio.sleep(2)
    return {
        "message": "Done with slow work",
        "handled_by": SERVER_NAME,
        "this_server_request_count": request_count,
    }


@app.get("/health")
async def health():
    """Health check — Nginx uses this to know if the server is alive."""
    return {"status": "healthy", "server": SERVER_NAME}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    import uvicorn
    print(f"Starting {SERVER_NAME} on port {args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)
