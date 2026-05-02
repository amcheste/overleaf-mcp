# Deployment overview

The HTTP transport (`overleaf-mcp serve-http`) is the right shape when you want claude.ai web — or any MCP client that can't spawn local subprocesses — to talk to your Overleaf project. The Python server itself only speaks plain HTTP; **TLS termination is the reverse proxy's job**, not the server's. That keeps the dep graph small and lets you pick whichever proxy you already know.

Three recipes, ranked by how simple they are:

| Recipe | When it fits | Setup time |
|---|---|---|
| [Caddy](caddy.md) | Starting from scratch on a VPS. Auto-provisions Let's Encrypt certificates with a 2-line config. **Recommended starting point.** | ~10 min |
| [nginx](nginx.md) | You already have nginx infrastructure. The overleaf-mcp specifics are minimal; it's standard reverse-proxy config | ~15 min |
| [Fly.io](fly-io.md) | One-command deploy with TLS handled automatically. Cheapest tier ($0–5/mo) is enough | ~10 min |

## What's the same regardless of recipe

- **Python server binds to loopback** (`127.0.0.1:8080` by default). Public traffic hits the proxy, not the server directly.
- **Auth is mandatory.** Set `OVERLEAF_MCP_AUTH_TOKEN` in the server's environment. Server refuses to start without it.
- **Endpoints:**
    - `POST /mcp/` — MCP wire protocol (trailing slash matters). Requires `Authorization: Bearer <token>`.
    - `GET /healthz` — monitoring. No auth required, returns `{"status": "ok"}`.

## Connecting claude.ai

Once a recipe is deployed, the claude.ai connector configuration is the same in all cases:

- **URL:** `https://your-host/mcp/` (trailing slash matters)
- **Auth:** Bearer token, value = the same token you set as `OVERLEAF_MCP_AUTH_TOKEN`

## Security checklist before exposing publicly

- TLS via the reverse proxy. The server speaks plain HTTP.
- Strong token. `openssl rand -hex 32` is good; anything shorter is not.
- Rotate the token whenever it leaks. Update the env var, restart the server.
- Consider IP allowlisting at the proxy if your access pattern is fixed.
