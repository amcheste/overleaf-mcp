# Caddy deployment

[Caddy](https://caddyserver.com/) is the simplest way to put TLS in
front of `overleaf-mcp serve-http`. It auto-renews Let's Encrypt
certificates, handles HTTP→HTTPS redirect, and the config is two lines.

This guide assumes:
- A VPS or similar host with a public IP
- A DNS A or AAAA record pointing your hostname at it
- Ports 80 and 443 open

## 1. Install Caddy

```sh
# Debian / Ubuntu
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

Other platforms: see [Caddy's install docs](https://caddyserver.com/docs/install).

## 2. Install overleaf-mcp-server

```sh
pipx install overleaf-mcp-server

# Configure your project (run interactively the first time)
overleaf-mcp init
overleaf-mcp auth add --project myproject
```

## 3. Generate a strong bearer token

```sh
openssl rand -hex 32
```

Copy the value. You'll use it both as the server's auth token and as
the credential clients send.

## 4. Run the server as a systemd service

Create `/etc/systemd/system/overleaf-mcp.service`:

```ini
[Unit]
Description=Overleaf MCP Server (HTTP transport)
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER
Environment="OVERLEAF_MCP_AUTH_TOKEN=PASTE_TOKEN_HERE"
ExecStart=/home/YOUR_USER/.local/bin/overleaf-mcp serve-http --host 127.0.0.1 --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Bind to `127.0.0.1` (loopback). Caddy will reverse-proxy to it. The
public internet never talks to the Python server directly.

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now overleaf-mcp
sudo systemctl status overleaf-mcp
```

## 5. Configure Caddy

Replace `/etc/caddy/Caddyfile` with:

```
overleaf-mcp.yourdomain.com {
    reverse_proxy 127.0.0.1:8080
}
```

That's the whole config. Caddy automatically:
- Provisions a Let's Encrypt certificate for `overleaf-mcp.yourdomain.com`
- Renews it before expiry
- Redirects HTTP to HTTPS
- Forwards every request to the local server, preserving headers
  (including `Authorization: Bearer ...`)

Reload Caddy:

```sh
sudo systemctl reload caddy
```

## 6. Test from your laptop

```sh
# Should return 200 OK with {"status":"ok"}
curl https://overleaf-mcp.yourdomain.com/healthz

# Should return 401 (no auth)
curl https://overleaf-mcp.yourdomain.com/mcp/

# Should return a different response (auth accepted)
curl -H "Authorization: Bearer PASTE_TOKEN_HERE" \
     https://overleaf-mcp.yourdomain.com/mcp/
```

## 7. Point claude.ai at it

In claude.ai's connector settings:
- URL: `https://overleaf-mcp.yourdomain.com/mcp/` (trailing slash matters)
- Auth: Bearer token, value = the same token you put in the systemd unit

## Operational notes

- **Logs:** `journalctl -u overleaf-mcp -f` for the Python server,
  `journalctl -u caddy -f` for the proxy. Set `OVERLEAF_MCP_DEBUG=1`
  in the systemd unit's Environment to bump server logging to DEBUG.
- **Token rotation:** generate a new token, update the systemd unit's
  `Environment=` line, `sudo systemctl restart overleaf-mcp`, update
  the credential in claude.ai. Old token stops working immediately.
- **Updates:** `pipx upgrade overleaf-mcp-server` then
  `sudo systemctl restart overleaf-mcp`.
- **Firewall:** only ports 80 and 443 should be open externally.
  Port 8080 stays loopback-only.
