---
hide:
  - navigation
---

# overleaf-mcp-server

<p align="center">
  <img src="images/banner.png" alt="Overleaf MCP Server" width="800">
</p>

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
</p>

---

## What it is

A local Model Context Protocol (MCP) server that gives Claude ten tools for working with an Overleaf project: reading files, listing sections, editing prose, creating and deleting files, and syncing back. Every change goes through Overleaf's per-project Git remote, so the round-trip is `Claude → MCP server → git push → Overleaf web UI`.

Two transport modes — same tools, different deployment shape:

- **stdio** — for **Claude Desktop** and **Claude Code**. Run as a subprocess on your machine, no network exposure.
- **HTTP** — for **claude.ai web** and any MCP client that can't spawn local subprocesses. Requires a bearer token; pair with a TLS-terminating reverse proxy for public access.

## What it is not

- Not a replacement for Overleaf
- Not a hosted multi-user service — single researcher, single Claude session
- Not a LaTeX compiler — Overleaf still does the rendering
- No branch / merge / diff tooling — use git directly for that
- No real-time collaboration with humans editing in the Overleaf web UI at the same moment

If those constraints feel restrictive, that's deliberate — see the [Security](security.md) page for the design rationale.

## Where to go from here

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Get started**

    ---

    Install, configure your first project, and connect Claude Desktop in five minutes.

    [→ Quickstart](quickstart.md)

-   :material-toolbox:{ .lg .middle } **What can it do?**

    ---

    Reference for all ten MCP tools, plus concrete prompts that show what they do in practice.

    [→ Tools](tools.md) · [→ Examples](examples.md)

-   :material-server-network:{ .lg .middle } **Deploy remotely**

    ---

    Run the HTTP transport behind Caddy, nginx, or on Fly.io so claude.ai web can use it.

    [→ Deployment](deployment/index.md)

-   :material-shield-check:{ .lg .middle } **Security model**

    ---

    What this server protects against, what it doesn't, and how to report a vulnerability.

    [→ Security](security.md)

</div>

## Install

```sh
pipx install overleaf-mcp-server
```

Or with `uv`:

```sh
uv tool install overleaf-mcp-server
```

Either gives you the `overleaf-mcp` command.
