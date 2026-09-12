"""
Test the Multi-User LLM Gateway.

Demonstrates:
  1. Two users (alice, bob) with SEPARATE credits + rate limits
  2. Rate limiting — 6 fast requests, the 6th gets blocked (429)
  3. Credit exhaustion — keep asking until credits run out (402)
  4. Usage dashboard — see everyone's spend

Run (after redis-server + multi_user_gateway.py are running):
    ../.venv/bin/python3 test_multi_user.py
"""

import httpx

API = "http://localhost:8000"


def ask(client, user, question):
    """Send a question as a given user (via X-User-Id header)."""
    return client.post(
        f"{API}/ask",
        json={"question": question},
        headers={"X-User-Id": user},
    )


def main():
    with httpx.Client(timeout=30) as client:
        # Start clean
        client.delete(f"{API}/admin/reset")
        print("=" * 60)
        print("  Multi-User LLM Gateway Test")
        print("=" * 60)

        # ------------------------------------------------------
        # 1. RATE LIMITING: alice sends 6 quick requests (limit is 5/min)
        # ------------------------------------------------------
        print("\n  [1] RATE LIMITING — alice sends 6 requests (limit 5/min):\n")
        # Give alice enough credits so ONLY the rate limit blocks her
        client.post(f"{API}/admin/topup/alice", params={"amount": 1.0})

        for i in range(1, 7):
            resp = ask(client, "alice", f"Say the number {i} only")
            if resp.status_code == 200:
                data = resp.json()
                print(f"    Request {i}: OK — credits left ${data['credits_remaining']:.6f}")
            elif resp.status_code == 429:
                print(f"    Request {i}: BLOCKED (429) — {resp.json()['detail']}")
            else:
                print(f"    Request {i}: {resp.status_code} — {resp.json().get('detail')}")

        # ------------------------------------------------------
        # 2. USER ISOLATION: bob is unaffected by alice's limit
        # ------------------------------------------------------
        print("\n  [2] USER ISOLATION — bob asks (separate limits from alice):\n")
        client.post(f"{API}/admin/topup/bob", params={"amount": 1.0})
        resp = ask(client, "bob", "Say hello")
        if resp.status_code == 200:
            print(f"    bob: OK — bob has his own limits, not affected by alice")
        else:
            print(f"    bob: {resp.status_code} — {resp.json().get('detail')}")

        # ------------------------------------------------------
        # 3. CREDIT EXHAUSTION: charlie gets a TINY budget so he runs out fast
        # ------------------------------------------------------
        print("\n  [3] CREDIT EXHAUSTION — charlie has a tiny $0.0001 budget:\n")
        # First create charlie by asking once, then set his balance very low.
        ask(client, "charlie", "hi")
        # Force his remaining credits to a tiny amount so the NEXT call exhausts it.
        client.post(f"{API}/admin/set/charlie", params={"amount": 0.00008})
        for i in range(1, 5):
            resp = ask(client, "charlie", "Write one sentence about Python")
            if resp.status_code == 200:
                data = resp.json()
                print(f"    Request {i}: OK — spent ${data['cost_this_call']:.6f}, "
                      f"left ${data['credits_remaining']:.6f}")
            elif resp.status_code == 402:
                print(f"    Request {i}: BLOCKED (402) — out of credits!")
                break
            elif resp.status_code == 429:
                print(f"    Request {i}: rate limited (429)")
                break

        # ------------------------------------------------------
        # 4. DASHBOARD: see everyone's usage
        # ------------------------------------------------------
        print("\n  [4] USAGE DASHBOARD — all users:\n")
        resp = client.get(f"{API}/usage")
        data = resp.json()
        print(f"    Total users: {data['total_users']}")
        for u in data["users"]:
            print(f"      {u['user']:8s} | spent ${u['total_spent']:.6f} | "
                  f"remaining ${u['credits_remaining']:.6f}")

    print("\n  Done! Notice:")
    print("    - alice hit the RATE limit (429) on her 6th request")
    print("    - bob was unaffected (separate per-user limits)")
    print("    - charlie hit the CREDIT limit (402) when broke")
    print("    - all state lives in Redis → works across many servers")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("\n  ERROR: Can't reach the API. Make sure BOTH are running:")
        print("    1. redis-server")
        print("    2. python3 multi_user_gateway.py")


