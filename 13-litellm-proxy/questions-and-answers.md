# LiteLLM / Proxy — All Questions & Answers

All the questions asked and answered while learning module 13.

---

## Difference between proxy and reverse proxy

Both sit in the middle and forward traffic, but they work on **opposite sides** and represent opposite parties.

**One-sentence version:**
- A **proxy (forward proxy)** sits in front of **clients** and represents them to the outside world. It hides *who is asking*.
- A **reverse proxy** sits in front of **servers** and represents them to the outside world. It hides *who is answering*.

**The mental model:**
```
FORWARD PROXY (protects/represents the client)

  [You] → [Proxy] → → → the internet → → → [Website]

  The website sees the PROXY's identity, not yours.


REVERSE PROXY (protects/represents the server)

  [User] → → → the internet → → → [Reverse Proxy] → [Server A]
                                                   → [Server B]
                                                   → [Server C]
  The user sees the REVERSE PROXY, not the real servers behind it.
```

The trick to remember: ask **"who is it standing in front of?"**
- Standing in front of the **clients** going out → forward proxy.
- Standing in front of the **servers** receiving traffic → reverse proxy.

**Side-by-side:**

| | Forward Proxy | Reverse Proxy |
|---|---|---|
| Sits in front of | Clients / users | Servers / backends |
| Acts on behalf of | The client | The server |
| Who it hides | The client's identity from the server | The servers' identity/structure from the client |
| Who configures it | The client (browser, OS, or company network) | The server operator |
| Client aware of it? | Yes — client explicitly points at it | No — client thinks it's talking to the real site |
| Typical goals | Anonymity, bypass geo-blocks, content filtering, caching for a group of users | Load balancing, SSL termination, caching, security shield, routing |

**Real-world examples:**

Forward proxy:
- A corporate network routing all employee web traffic through a proxy to filter/block sites and log usage.
- A VPN or anonymizing proxy that makes a website think your request comes from another country.
- School/office content filters.

Reverse proxy:
- **Nginx** in front of your app servers (see `11-nginx-loadbalancing/nginx.conf`).
- **Cloudflare** in front of a website for DDoS protection and caching.
- An API gateway / load balancer distributing requests across many backend instances.

**How this connects to this repo:**
- `11-nginx-loadbalancing/nginx.conf` is a **reverse proxy** — Nginx receives requests and distributes them across multiple backend app instances. The client only ever sees Nginx.
- `13-litellm-proxy/` — LiteLLM acts as a **reverse proxy / gateway** in front of multiple LLM providers (OpenAI, Anthropic, Groq...). Your app talks to one endpoint (LiteLLM), and it routes to whichever real provider is behind it, handling keys, load, and fallbacks.
