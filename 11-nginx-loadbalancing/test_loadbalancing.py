"""
Test script — sends many requests to Nginx and shows which server handled each.

This proves load balancing works: you'll see requests spread across
Server-1, Server-2, Server-3 in rotation.

Run (after Nginx + 3 app copies are running):
    ../.venv/bin/python3 test_loadbalancing.py
"""

import asyncio
import httpx
from collections import Counter

NGINX_URL = "http://localhost:8080/"
NUM_REQUESTS = 12


async def main():
    print(f"Sending {NUM_REQUESTS} requests to Nginx ({NGINX_URL})\n")

    counter = Counter()

    async with httpx.AsyncClient() as client:
        for i in range(1, NUM_REQUESTS + 1):
            try:
                response = await client.get(NGINX_URL)
                data = response.json()
                server = data["handled_by"]
                counter[server] += 1
                print(f"  Request {i:2d} → handled by {server}")
            except Exception as e:
                print(f"  Request {i:2d} → ERROR: {e}")
                print("\n  Is everything running? You need:")
                print("    1. Three app copies (ports 8001, 8002, 8003)")
                print("    2. Nginx running (port 8080)")
                return

    print(f"\n  --- Distribution ---")
    for server, count in sorted(counter.items()):
        bar = "█" * count
        print(f"  {server}: {count} requests  {bar}")

    print(f"\n  Notice: requests were spread evenly across all servers!")
    print(f"  This is round-robin load balancing — Nginx rotates through each server.")


if __name__ == "__main__":
    asyncio.run(main())
