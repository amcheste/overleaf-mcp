# nginx deployment

For users on existing nginx infrastructure. If you're starting from
scratch, [Caddy](caddy.md) is simpler: auto-TLS in two lines of config.
nginx is the right pick when you already have an nginx server you want
this to live alongside.

This guide assumes you know your way around nginx + certbot. The
overleaf-mcp specifics are minimal; the bulk is standard reverse-proxy
config.

## 1. Install overleaf-mcp-server and a systemd service

Identical to the [Caddy guide](caddy.md#2-install-overleaf-mcp-server)
through step 4. Bind the Python server to `127.0.0.1:8080`.

## 2. nginx site config

Create `/etc/nginx/sites-available/overleaf-mcp` (or wherever your
distro keeps server blocks):

```nginx
server {
    listen 80;
    server_name overleaf-mcp.yourdomain.com;

    # Redirect everything to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name overleaf-mcp.yourdomain.com;

    # Certbot will populate these (see step 3).
    ssl_certificate     /etc/letsencrypt/live/overleaf-mcp.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/overleaf-mcp.yourdomain.com/privkey.pem;

    # Recommended baseline (see Mozilla SSL Configurator for current values)
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;

        # Pass through the bearer token unmodified
        proxy_set_header Authorization $http_authorization;

        # Standard reverse-proxy headers
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streamable HTTP can issue long-running requests; bump the
        # default 60s read timeout so the proxy doesn't kill in-flight
        # tool calls.
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        # Don't buffer responses. The MCP transport streams.
        proxy_buffering off;
    }
}
```

Enable the site and reload:

```sh
sudo ln -s /etc/nginx/sites-available/overleaf-mcp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 3. TLS via certbot

```sh
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d overleaf-mcp.yourdomain.com
```

Certbot edits the nginx config in place to use the cert it just
provisioned and sets up auto-renewal via a cron job / systemd timer.

## 4. Test

```sh
# Healthz, no auth required
curl https://overleaf-mcp.yourdomain.com/healthz

# /mcp/ without auth: expect 401
curl -i https://overleaf-mcp.yourdomain.com/mcp/

# /mcp/ with auth: expect MCP response
curl -i -H "Authorization: Bearer YOUR_TOKEN" https://overleaf-mcp.yourdomain.com/mcp/
```

## 5. Wire up claude.ai

URL: `https://overleaf-mcp.yourdomain.com/mcp/` (trailing slash matters)
Auth: Bearer token

## Common nginx pitfalls

- **Stripped `Authorization` header.** Some nginx setups strip
  `Authorization` going to upstream. The explicit
  `proxy_set_header Authorization $http_authorization;` line above
  prevents this. If you see 401s despite passing the right token at the
  edge, check this first.
- **Default 60s read timeout.** Long-running tool calls (e.g. a large
  `edit_file` that triggers a slow Overleaf push) can exceed it. The
  300s timeouts in the config above usually suffice; bump higher if you
  see truncated responses.
- **HTTP/1.1 required.** `proxy_http_version 1.1` is needed for
  Streamable HTTP to work properly. Without it, responses can stall.
