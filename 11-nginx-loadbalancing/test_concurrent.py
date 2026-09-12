"""
Concurrent test — sends requests AT THE SAME TIME to see least_conn differ from round robin.

Why this test exists:
    The basic test_loadbalancing.py sends requests ONE AT A TIME (sequential).
    With sequential requests, all servers are always idle (0 connections),
    so least_conn looks identical to round robin.

    least_conn only shows its difference when requests OVERLAP (are concurrent)
    and take different amounts of time. This test does that.

Run (after Nginx + 3 servers are running):
    ../.venv/bin/python3 test_concurrent.py

To compare:
    1. Run with round robin (default config) - note the distribution
    2. Edit nginx.conf: uncomment 'least_conn;', run 'nginx -s reload'
    3. Run this again - compare
"""

import asyncio
import httpx
from collections import Counter

NGINX_URL = "http://localhost:8080/slow"  # the SLOW endpoint (2s each) - makes connections overlap
NUM_REQUESTS = 12


async def send_one(client, i, counter):
    """Send one request and record which server handled it."""
    try:
        response = await client.get(NGINX_URL, timeout=30)
        server = response.json()["handled_by"]
        counter[server] += 1
        print(f"  Request {i:2d} → {server}")
    except Exception as e:
        print(f"  Request {i:2d} → ERROR: {e}")


async def main():
    print(f"Sending {NUM_REQUESTS} CONCURRENT requests to {NGINX_URL}")
    print("(All fired at once, so servers get busy and connections overlap)\n")

    counter = Counter()

    async with httpx.AsyncClient() as client:
        # Fire ALL requests at the same time (concurrent, not one-by-one)
        tasks = [send_one(client, i, counter) for i in range(1, NUM_REQUESTS + 1)]
        await asyncio.gather(*tasks)

    print(f"\n  --- Distribution ---")
    for server, count in sorted(counter.items()):
        bar = "█" * count
        print(f"  {server}: {count} requests  {bar}")

    print(f"\n  With concurrent requests:")
    print(f"    round robin  → still spreads evenly (ignores how busy each server is)")
    print(f"    least_conn   → favors whichever server frees up first")
    print(f"  (Difference is clearer with more requests and varying response times.)")


if __name__ == "__main__":
    asyncio.run(main())
