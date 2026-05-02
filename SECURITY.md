# Security policy

## Supported versions

Security fixes target the latest minor release. Older 0.x lines are not
backported — if you're on an old version, upgrade first.

| Version line | Supported |
|---|---|
| 0.3.x | ✅ |
| 0.2.x | upgrade to 0.3.x |
| 0.1.x | upgrade to 0.3.x |

## Reporting a vulnerability

**Please do not file a public GitHub issue for security reports.**

Use GitHub's private vulnerability reporting:

1. Go to the [Security tab](https://github.com/amcheste/overleaf-mcp/security)
2. Click **Report a vulnerability**
3. Fill in details — what you found, how to reproduce, what you think the impact is

Or email `amcheste+security@gmail.com` if you'd rather not use GitHub.

You should hear back within a few days. I'll work with you on a fix and a
coordinated disclosure timeline. Critical issues that affect deployed
users will get a patched release as fast as I can verify the fix.

## Threat model — what this server protects against, and what it doesn't

The server is designed for **a single researcher running it locally or on
a personal VPS**. The threat model is shaped by that.

### What the design protects

- **Tokens never on disk in plaintext.** Overleaf tokens live in the OS
  keychain (`keyring` library). The config file at
  `~/.config/overleaf-mcp/config.toml` contains aliases and project IDs
  only.
- **Tokens never in subprocess argv.** Git invocations use a transient
  `GIT_ASKPASS` script reading credentials from environment variables.
  `ps`-style process snapshots don't reveal the token.
- **Path-escape attempts are rejected up-front.** `validate_path` blocks
  absolute paths (POSIX *and* Windows formats), `../` escapes, and
  symlinks pointing outside the repo root. Defense-in-depth — every
  write tool re-validates regardless of caller.
- **HTTP transport requires bearer auth.** `serve-http` refuses to start
  without `OVERLEAF_MCP_AUTH_TOKEN`. Token check uses
  `hmac.compare_digest` so timing on a partial-match attempt doesn't
  leak the token byte-by-byte.
- **No telemetry.** The server only contacts `git.overleaf.com` and the
  local filesystem. No analytics, no error reporting service, no
  background phone-home.

### What the design does NOT protect against

- **A compromised local machine.** If an attacker has root or your user
  account on the machine running the server, they can read the keychain
  the same way the server does. There's no protection against
  same-user compromise.
- **Multi-tenant misuse.** The server is single-user. If you expose the
  HTTP transport to multiple users with the same bearer token, they
  share access to every Overleaf project in your config. Don't do that.
- **Malicious Overleaf projects.** If you add a project alias for a
  remote you don't control, that remote can serve you arbitrary git
  content. The server doesn't sandbox what it pulls.
- **MITM on the HTTP transport.** The server speaks plain HTTP. Public
  deployments must terminate TLS at a reverse proxy (Caddy, nginx,
  Cloudflare). Without TLS the bearer token is in cleartext on the
  wire.
- **Supply chain attacks on dependencies.** We pin via `uv.lock` and
  Dependabot keeps deps fresh, but a compromised upstream
  (`mcp`, `keyring`, `pydantic`, `click`) would compromise this server
  too. Standard Python packaging caveats apply.

### Reporting scope

Security reports in scope:
- Token leaks (logs, argv, error messages, disk artifacts)
- Path-escape bypasses on `validate_path`
- Auth bypasses on the HTTP transport
- Crashes that allow arbitrary command execution
- Anything that makes the server a credential-stealing vector

Out of scope (file a regular issue instead):
- "What if the user's machine is already compromised" — yes, it'd be bad
- Bugs in upstream dependencies — report them upstream
- Feature requests for hardened multi-tenant operation — different design
