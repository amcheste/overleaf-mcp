# Quickstart

Two paths depending on which Claude client you're targeting:

- **stdio** for Claude Desktop and Claude Code (this is what most people want)
- **HTTP** for claude.ai web

## Requirements

- Python 3.11 or newer
- A **paid** Overleaf account (Git integration is a paid feature)
- An Overleaf Git authentication token: Overleaf web UI → Account Settings → Git Integration → New token
- `git` on your `PATH`
- `git config user.name` and `git config user.email` set globally (the server signs commits with this identity)

## Install

```sh
pipx install overleaf-mcp-server
```

Or with `uv`:

```sh
uv tool install overleaf-mcp-server
```

Either gives you the `overleaf-mcp` command.

## Local setup (Claude Desktop / Claude Code)

### 1. Configure a project alias

```sh
overleaf-mcp init
#   Project alias (short nickname): my-paper
#   Overleaf project ID: 5f4a...           # from the project URL on overleaf.com
#   Display name (optional): My Paper
```

Or scripted:

```sh
overleaf-mcp init \
    --alias my-paper \
    --project-id 5f4a... \
    --display-name "My Paper"
```

### 2. Store your Overleaf token

```sh
overleaf-mcp auth add --project my-paper
#   Overleaf token: ****                    # paste, hidden input
```

For CI / scripts, pipe via stdin:

```sh
printf '%s' "$OVERLEAF_TOKEN" | overleaf-mcp auth add --project my-paper --token-stdin
```

### 3. Clone the project

```sh
overleaf-mcp project clone my-paper
```

### 4. Verify

```sh
overleaf-mcp doctor
```

`doctor` prints a clean pass/fail report. If everything is green you're ready to wire up Claude Desktop.

### 5. Wire up Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add:

```json
{
  "mcpServers": {
    "overleaf": {
      "command": "overleaf-mcp",
      "args": ["serve"]
    }
  }
}
```

**Fully quit** and relaunch Claude Desktop (`cmd-Q` on macOS — closing the window isn't enough). In a new conversation, ask Claude something like *"use overleaf list_projects"* to verify.

## Remote setup (claude.ai web)

For claude.ai web — anything that can't spawn local subprocesses.

### 1. Generate a strong bearer token

```sh
export OVERLEAF_MCP_AUTH_TOKEN="$(openssl rand -hex 32)"
```

The server refuses to start without this, because the keychain holds your Overleaf tokens and HTTP exposure without auth would expose them to anyone who can reach the bound port. There is no "open mode" flag.

### 2. Run the HTTP transport

```sh
# Loopback only (safe for local-only access)
overleaf-mcp serve-http

# Or bind public + put TLS in front (see Deployment guides)
overleaf-mcp serve-http --host 0.0.0.0 --port 8080
```

### 3. Point claude.ai at it

In claude.ai's connector settings, point at `https://your-host/mcp/` (trailing slash matters) and set the bearer token. claude.ai handles the rest.

For production-quality deployment (TLS via reverse proxy, systemd unit, etc.), see the [Deployment](deployment/index.md) recipes.
