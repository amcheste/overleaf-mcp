<p align="center">
  <img src="docs/images/banner.png" alt="Overleaf MCP Server" width="800">
</p>

<h1 align="center">Overleaf MCP Server</h1>

<p align="center">
  <strong>Edit your Overleaf projects from Claude.</strong><br>
  Local, auditable, single-user by design.
</p>

<p align="center">
  <a href="https://pypi.org/project/overleaf-mcp-server/"><img alt="PyPI" src="https://img.shields.io/pypi/v/overleaf-mcp-server.svg"></a>
  <a href="https://pypi.org/project/overleaf-mcp-server/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/overleaf-mcp-server.svg"></a>
  <a href="https://github.com/amcheste/overleaf-mcp/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/overleaf-mcp-server.svg"></a>
  <a href="https://github.com/amcheste/overleaf-mcp/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/amcheste/overleaf-mcp/actions/workflows/tests.yml/badge.svg?branch=develop"></a>
  <a href="https://codecov.io/gh/amcheste/overleaf-mcp"><img alt="Coverage" src="https://codecov.io/gh/amcheste/overleaf-mcp/branch/develop/graph/badge.svg"></a>
  <a href="https://pepy.tech/project/overleaf-mcp-server"><img alt="Downloads" src="https://static.pepy.tech/badge/overleaf-mcp-server/month"></a>
</p>

---

## What it is

A local Model Context Protocol server that gives Claude five tools for working with an Overleaf project: `list_projects`, `list_files`, `read_file`, `edit_file`, `sync`. Every change goes through Overleaf's per-project Git remote, so the round-trip is `Claude → MCP server → git push → Overleaf web UI`.

## What it is not

- Not a replacement for Overleaf
- Not a hosted multi-user service — single researcher, single Claude session, stdio transport
- Not a LaTeX compiler — Overleaf still does the rendering
- No branch / merge / diff tooling — use git directly for that
- No real-time collaboration with humans editing in the Overleaf web UI at the same moment (use Overleaf's native real-time collab for that; the MCP server pulls before every write to stay honest, but doesn't subscribe to live updates)

If those constraints feel restrictive, that's deliberate — see the [project notes](CLAUDE.md) for the design rationale.

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

or with `uv`:

```sh
uv tool install overleaf-mcp-server
```

Either gives you the `overleaf-mcp` command.

## Quick start

### Interactive setup

```sh
# 1. Configure a project alias
overleaf-mcp init
#   Project alias (short nickname): my-paper
#   Overleaf project ID: 5f4a...           # from the project URL on overleaf.com
#   Display name (optional): My Paper

# 2. Store your Overleaf token in the OS keychain
overleaf-mcp auth add --project my-paper
#   Overleaf token: ****                    # paste, hidden input

# 3. Clone the project locally (one-time)
git clone https://git.overleaf.com/<project_id> ~/.cache/overleaf-mcp/my-paper

# 4. Verify
overleaf-mcp doctor
```

### Scripted setup (v0.1.2+)

For provisioning scripts and CI, every prompt above has a flag-based equivalent:

```sh
# 1. Configure non-interactively (--alias engages non-interactive mode)
overleaf-mcp init \
    --alias my-paper \
    --project-id 5f4a... \
    --display-name "My Paper"
# add --force to overwrite an existing alias without prompting

# 2. Store the token via stdin (preferred — keeps it off the process command line)
printf '%s' "$OVERLEAF_TOKEN" | overleaf-mcp auth add --project my-paper --token-stdin

# or read from a named environment variable
overleaf-mcp auth add --project my-paper --token-from-env OVERLEAF_TOKEN

# 3. Clone the project (same as interactive)
git clone "https://x:${OVERLEAF_TOKEN}@git.overleaf.com/<project_id>" \
    ~/.cache/overleaf-mcp/my-paper

# 4. Verify
overleaf-mcp doctor
```

There is intentionally no `--token VALUE` flag.  Values on the command line leak via `ps`; pipe through stdin or use an env var instead.

`doctor` prints a clean pass/fail report. If everything is green you're ready to wire up Claude Desktop.

### Claude Desktop configuration

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

Fully quit and relaunch Claude Desktop (cmd-Q on macOS — closing the window isn't enough). In a new conversation, ask Claude something like *"use overleaf list_projects"* to verify.

## Remote deployment (HTTP, for claude.ai web)

If you want to use the server with **claude.ai web** or any other MCP client that can't spawn local subprocesses, run it as an HTTP server. Same tools, different transport.

**Required:** a strong bearer token. The server refuses to start without `OVERLEAF_MCP_AUTH_TOKEN` set, because it would otherwise expose every Overleaf token in your keychain to anyone who can reach the bound port.

```sh
# Generate a token
export OVERLEAF_MCP_AUTH_TOKEN="$(openssl rand -hex 32)"

# Run on loopback (default; safe for local-only access)
overleaf-mcp serve-http

# Or bind public + put a TLS-terminating reverse proxy in front
overleaf-mcp serve-http --host 0.0.0.0 --port 8080
```

Endpoints:
- **`POST /mcp/`** — the MCP endpoint. Requires `Authorization: Bearer <token>`. Trailing slash matters.
- **`GET /healthz`** — monitoring. Returns `{"status": "ok"}` with no auth.

In claude.ai's connector settings, point at `https://your-host/mcp/` and set the bearer token. claude.ai handles the rest.

**Security checklist before exposing publicly:**
- TLS via reverse proxy (nginx, caddy, cloudflare). The server speaks plain HTTP.
- Strong token. `openssl rand -hex 32` is good; anything shorter is not.
- Rotate the token whenever it leaks. Update `OVERLEAF_MCP_AUTH_TOKEN` and restart.
- Consider IP allowlisting at the proxy if your access pattern is fixed.

## Tools

| Tool | What it does |
|---|---|
| `list_projects` | Lists configured Overleaf project aliases |
| `list_files` | Lists files tracked in the project's git clone (optional extension filter) |
| `read_file` | Reads a file from the project |
| `get_sections` | Lists LaTeX sections in a `.tex` file with level + line range |
| `get_section_content` | Returns the body of a named section |
| `edit_file` | Pulls latest, overwrites a file, commits, pushes to Overleaf |
| `create_file` | Creates a new file (errors if it already exists) |
| `delete_file` | Deletes a file from the project |
| `sync` | Pulls latest from Overleaf into the local clone |
| `project_status` | File count, dirty state, last-commit summary |

For concrete usage prompts and recipes, see [EXAMPLES.md](EXAMPLES.md).

## Troubleshooting

When something doesn't work, run `overleaf-mcp doctor` first — it
diagnoses most setup problems and prints the exact command to fix them.
Common cases beyond that:

| Symptom | Likely cause | Fix |
|---|---|---|
| `doctor` says **Token: FAIL** | No token registered for that alias | `overleaf-mcp auth add --project <alias>` |
| `doctor` says **Remote: FAIL** | Wrong/revoked Overleaf token, or network blocked | Re-issue the Overleaf token (Account Settings → Git Integration), then `overleaf-mcp auth add --project <alias>` again |
| `doctor` says **Clone: missing** | Project not cloned yet | `overleaf-mcp project clone <alias>` |
| `doctor` says **Git author: FAIL** | System git config missing user.name / user.email | `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"` |
| `serve-http` exits immediately with `OVERLEAF_MCP_AUTH_TOKEN is not set` | The HTTP transport refuses to start without auth | `export OVERLEAF_MCP_AUTH_TOKEN="$(openssl rand -hex 32)"` then re-run |
| Claude Desktop sees no tools | Either config file isn't valid JSON, or Claude Desktop wasn't fully quit (cmd-Q) | Validate JSON, then cmd-Q (not just close window) and reopen |
| claude.ai web returns 401 | Wrong bearer token, or wrong scheme (`Basic` instead of `Bearer`), or missing trailing slash on `/mcp/` | Check all three — the URL must be `https://your-host/mcp/` with a trailing slash |
| `edit_file` fails with `git push --ff-only` rejected | Someone (or the Overleaf web UI) edited the project after your last pull | The next `edit_file` will pull first and try again. If it persists, the local clone has diverged — `cd ~/.cache/overleaf-mcp/<alias> && git status` to inspect |

For HTTP-transport deployment beyond local use, see the recipes under
[`docs/deployment/`](docs/deployment/) — Caddy, nginx, and Fly.io
walkthroughs.

## GitHub mirror (optional)

The MCP server only knows about your Overleaf remote. If you want a GitHub backup of a project, add it as a second remote on the local clone:

```sh
cd ~/.cache/overleaf-mcp/my-paper
git remote add github git@github.com:you/my-paper-mirror.git
git push github main
```

Then `git push github main` whenever you want to update the mirror, or wire up a cron / launchd job. The MCP server intentionally doesn't manage GitHub — that boundary keeps the server's surface small and the mirror under your control.

## Security

- Tokens are stored in the OS keychain (`keyring` library — macOS Keychain, Windows Credential Manager, libsecret on Linux). Never on disk.
- The config file (`~/.config/overleaf-mcp/config.toml`) contains aliases and project IDs only — no secrets. Safe to put under version control if you really want to.
- Subprocess git invocations pass tokens via env vars consumed by a transient `GIT_ASKPASS` script. Tokens never appear on the subprocess command line, so they don't show in `ps`.
- The server only talks to `git.overleaf.com` and the local filesystem. No telemetry, no analytics, no other network traffic.

## Limitations

- **Regex section parser.** Handles `\section`, `\subsection`, `\subsubsection` (and starred variants) at the start of a line. Doesn't follow `\input{}` / `\include{}` across files, doesn't expand custom section macros, and doesn't parse titles with nested `{}` groups. Swap-in of a `pylatexenc`-backed parser is staged behind the abstract base class for a future minor release.
- **Single-user assumption.** No locks, no concurrent-edit detection beyond `git pull --ff-only` (which fails fast if the local clone has diverged). Real-time collaboration with humans editing in the Overleaf web UI works because the server pulls before every write, but it's not a streaming sync.
- **stdio transport only in v0.1.** HTTP/SSE for remote / multi-client setups is staged for v0.2.
- **No clone orchestration.** `doctor` reports if the local clone is missing and prints the `git clone` command; the MCP server itself doesn't create or refresh the cache. Plain git is the right tool there.

## Contributing

Bug reports and PRs welcome. See [CLAUDE.md](CLAUDE.md) for project-local design notes if you're working on the server itself.

## License

MIT — see [LICENSE](LICENSE).
