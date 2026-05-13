# Overleaf MCP Server: architecture notes

Project-local context for Claude sessions. The [README.md](README.md) is for end users; this file is for contributors (human or AI) working on the server itself.

## The write path IS git

Overleaf does not expose a public HTTP write API for project file trees. The only supported programmatic write path on a paid Overleaf account is the per-project Git remote at `git.overleaf.com/<project_id>`.

This server is therefore a local git client:

```
Claude ──MCP─► overleaf-mcp ──git-over-HTTPS──► git.overleaf.com
               (cached local clone)
```

Every write tool (`edit_file`, `create_file`, `delete_file`) follows the same flow:

1. `git pull` to refresh the cached clone
2. Validate the target path stays inside the repo root
3. Write/delete the file in the working tree
4. `git commit` with a generated message and the configured author
5. `git push` to Overleaf

If you ever find yourself reaching for an "Overleaf REST API" call, stop. There isn't one. The answer is always a git operation against the cached clone.

We shell out to `git` via `subprocess` rather than using GitPython. The design goal is auditability: the dependency graph should be readable in five minutes.

## GitHub mirroring is out of scope

Users who want a GitHub backup add GitHub as a second remote on their own local clone. The MCP server knows nothing about GitHub and should not grow GitHub-aware code. If this boundary ever gets tempted, push back.

## Credentials never touch disk

Tokens live in the OS keychain (primary) or environment variables (fallback, for CI/power users). The config file contains project aliases + IDs only, never tokens. See [src/overleaf_mcp/core/credentials.py](src/overleaf_mcp/core/credentials.py) for the resolution order.

## Scope discipline

This server is deliberately single-process, single-user, stdio-transport, serial. No Redis, no job queues, no locks, no concurrent-edit handling. Those assumptions keep the code auditable and are why we can ship something meaningfully different from the existing community servers. If you find yourself adding coordination machinery, stop and re-read this section.
