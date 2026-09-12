# 11 - Nginx Load Balancing (on your Mac)

See Nginx load balancing in action locally. You'll run 3 copies of a FastAPI app,
put Nginx in front, and watch requests get spread across all 3.

```
                        ┌→ Server-1 (port 8001)
Browser → Nginx (8080) ─┼→ Server-2 (port 8002)
                        └→ Server-3 (port 8003)
```

## What's in this folder
- `app.py` — a simple FastAPI app (each copy knows its own name)
- `nginx.conf` — Nginx config that load-balances 3 copies
- `test_loadbalancing.py` — sends 12 requests, shows which server handled each

---

## Setup (one time)

**1. Install Nginx:**
```bash
brew install nginx
```

**2. Install httpx (for the test script):**
```bash
uv pip install httpx --python ../.venv/bin/python3
```

---

## Running the demo

You'll need **5 terminals** (or use the all-in-one script below).

### Terminal 1 — Server 1
```bash
cd 11-nginx-loadbalancing
SERVER_NAME="Server-1" ../.venv/bin/python3 app.py --port 8001
```

### Terminal 2 — Server 2
```bash
cd 11-nginx-loadbalancing
SERVER_NAME="Server-2" ../.venv/bin/python3 app.py --port 8002
```

### Terminal 3 — Server 3
```bash
cd 11-nginx-loadbalancing
SERVER_NAME="Server-3" ../.venv/bin/python3 app.py --port 8003
```

### Terminal 4 — Nginx
```bash
cd 11-nginx-loadbalancing
nginx -c "$(pwd)/nginx.conf"
```
(Nginx runs in foreground. Stop it with Ctrl+C.)

### Terminal 5 — Test it
```bash
cd 11-nginx-loadbalancing
../.venv/bin/python3 test_loadbalancing.py
```

You'll see output like:
```
  Request  1 → handled by Server-1
  Request  2 → handled by Server-2
  Request  3 → handled by Server-3
  Request  4 → handled by Server-1
  ...

  --- Distribution ---
  Server-1: 4 requests  ████
  Server-2: 4 requests  ████
  Server-3: 4 requests  ████
```

That's load balancing! Nginx rotated requests across all 3 servers evenly.

---

## Try it in your browser too

Open http://localhost:8080 and refresh a few times.
Watch the `handled_by` field change: Server-1 → Server-2 → Server-3 → repeat.

---

## Experiments to try

**1. Kill a server** — stop Terminal 2 (Ctrl+C). Run the test again.
Nginx notices Server-2 is dead and only uses Server-1 and Server-3.
(This is failover — one server dying doesn't break your app.)

**2. Change the load balancing strategy** — edit `nginx.conf`:
- Uncomment `least_conn;` → sends to the least-busy server
- Uncomment `ip_hash;` → same client always hits the same server (sticky sessions)

After editing, reload Nginx:
```bash
nginx -s reload
```

**3. See it handle concurrent load** — hit the `/slow` endpoint from multiple
terminals at once. Watch different servers handle them in parallel.

---

## Stopping everything

```bash
# Stop Nginx
nginx -s stop

# Stop each app copy: Ctrl+C in its terminal
```

---

## Key takeaways

- **Nginx doesn't create the app copies** — you started them yourself. Nginx just routes.
- **Round robin** (default) = rotate evenly through servers.
- **Health/failover** = if a server dies, Nginx skips it automatically.
- This is exactly what happens in production — just with more servers and an
  auto-scaler (Kubernetes/AWS) creating/removing copies based on load.
- On AWS, an **Application Load Balancer (ALB)** does this same job as a managed service.
