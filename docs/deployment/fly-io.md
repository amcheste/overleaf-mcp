# Fly.io deployment

Fly.io gives you a single-command deploy with TLS handled automatically.
Cheapest tier (`shared-cpu-1x`, 256 MB) is fine — the server is
single-process and doesn't hold much in memory.

## 1. Prep

Install [`flyctl`](https://fly.io/docs/hands-on/install-flyctl/) and
sign in:

```sh
brew install flyctl    # macOS
flyctl auth signup     # or 'auth login' if you have an account
```

## 2. Create a Dockerfile

The MCP server is pure Python — a slim base image works. Drop this in
the project root:

```dockerfile
# Dockerfile
FROM python:3.13-slim

# Git is required at runtime — the server shells out to it for every
# pull/push against git.overleaf.com.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir overleaf-mcp-server

# A non-root user. The keychain isn't used in this deployment (we hit
# Overleaf via project-scoped token in env), so no special perms needed.
RUN useradd -m -u 1000 app
USER app
WORKDIR /home/app

# Bind on all interfaces — Fly's edge handles TLS and forwards to here.
EXPOSE 8080
CMD ["overleaf-mcp", "serve-http", "--host", "0.0.0.0", "--port", "8080"]
```

## 3. Initialise the Fly app

```sh
flyctl launch --no-deploy
```

This generates a `fly.toml` and registers the app. You can accept the
defaults; we'll edit `fly.toml` next.

## 4. Configure `fly.toml`

```toml
# fly.toml — keep flyctl's generated app/region values, adjust the
# service block to look like this:

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true       # spin down when idle to save credits
  auto_start_machines = true      # spin up on first request
  min_machines_running = 0

[[http_service.checks]]
  interval = "30s"
  timeout = "5s"
  grace_period = "10s"
  method = "GET"
  path = "/healthz"
```

The `[[http_service.checks]]` block points at the `/healthz` endpoint
(which is exempt from auth) so Fly's load balancer can verify the
server's alive without a credential.

## 5. Set the auth token as a Fly secret

```sh
flyctl secrets set OVERLEAF_MCP_AUTH_TOKEN="$(openssl rand -hex 32)"
```

Save the token value somewhere safe — you'll need it for claude.ai
later. Fly secrets are encrypted at rest and injected as env vars at
runtime.

## 6. Deploy

```sh
flyctl deploy
```

Fly builds the image, runs the health check, and routes traffic when
it's healthy. URL is printed at the end; it'll be something like
`https://your-app-name.fly.dev`.

## 7. Test

```sh
# Healthz works without auth
curl https://your-app-name.fly.dev/healthz

# /mcp/ requires bearer
curl -i -H "Authorization: Bearer $OVERLEAF_MCP_AUTH_TOKEN" \
     https://your-app-name.fly.dev/mcp/
```

## 8. Wire up claude.ai

URL: `https://your-app-name.fly.dev/mcp/` (trailing slash matters)
Auth: Bearer, value = the secret you set in step 5

## Operational notes

- **Updating to a new server version:**
  ```sh
  # Bump the pip install version in Dockerfile, then:
  flyctl deploy
  ```
  (Or pin to a specific version — `pip install overleaf-mcp-server==X.Y.Z` —
  for reproducibility.)
- **Rotating the auth token:**
  ```sh
  flyctl secrets set OVERLEAF_MCP_AUTH_TOKEN="$(openssl rand -hex 32)"
  ```
  Fly restarts the machine automatically. Old token stops working as
  soon as the new machine takes traffic.
- **Logs:** `flyctl logs` for live tail, `flyctl logs --no-tail` for
  recent.
- **Project configuration is per-deploy.** This deployment doesn't have
  the OS keychain available — you can't run `overleaf-mcp init` /
  `overleaf-mcp auth add` interactively against a remote machine.
  Instead, set per-project tokens via additional Fly secrets like
  `OVERLEAF_TOKEN_MYPROJECT` (the env-var fallback the server already
  honors) and bake the config TOML into the image. For most users this
  is more friction than it's worth — Fly is a good fit if you want
  *one* project served remotely; for many projects, a VPS with the
  keychain is easier.
