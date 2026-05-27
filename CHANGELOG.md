# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The 0.x line signals iteration; the v1.0 API surface will be committed to once the tool list stabilises.

## [Unreleased]

## [0.4.1] - 2026-05-27

_First published release of the 0.4.x line. [0.4.0] was tagged (2026-05-12) but never reached PyPI — see Fixed. 0.4.1 ships all of 0.4.0's changes (listed below) with the release-pipeline issue resolved._

### Fixed

- **The release pipeline no longer blocks on the live Overleaf write suite.** Overleaf git write is a premium-only feature, so gating the PyPI publish on a live paid credential made releases brittle: when the test project's Overleaf premium lapsed, writes began returning HTTP 403, which silently blocked the v0.4.0 publish. The release `acceptance` job and the per-PR `real-overleaf` job are now non-blocking signals; `nightly.yml` remains the dedicated daily canary.

### Changed

- CI dependency/action bumps: `actions/deploy-pages` 4→5, `actions/upload-pages-artifact` 3→5, `actions/checkout` 4→6, plus grouped Python dependency updates.

## [0.4.0] - 2026-05-12

### Added

- **Acceptance test suite** (`tests/acceptance/`): 13 end-to-end tests against a real Overleaf project covering every tool (read, write, sync). Each test does the action via the actual MCP tool handler and verifies the change reached Overleaf by re-cloning fresh.
- **Acceptance gate on releases.** `release.yml` now runs the acceptance suite before build/publish. A failing acceptance test blocks the PyPI publish.
- **Nightly canary** (`nightly.yml`): runs the acceptance suite at 06:00 UTC daily and opens a GitHub issue on failure. Catches upstream changes (Overleaf API, mcp SDK, token rotation overdue) within ~24h.
- `pytest -m acceptance` opt-in pattern; default `pytest` run excludes the suite via `addopts`. Suite skips cleanly without `OVERLEAF_TEST_*` secrets so forks and local dev never try to hit a remote they can't authenticate against.
- **Brand banner** (`assets/banner.{svg,png}`) per [`banner-spec.md`](https://github.com/amcheste/alanchester-brand/blob/main/docs/banner-spec.md). README references the SVG at the top.
- **MkDocs Material documentation site** + GitHub Pages deploy workflow + README docs badge.
- **Codecov upload** from CI; Coverage and Downloads badges on README.
- **CONTRIBUTING.md**, **EXAMPLES.md**, deployment recipes, README troubleshooting section.
- **Dependabot** for actions + dependencies; pre-commit hooks.

### Changed

- README badges and prose aligned to brand system (license in Hunter Green, version in Ink).
- Dependency bumps: `codecov-action` 5 → 6, `setup-uv` 3 → 7, `download-artifact` 4 → 8, `setup-python` 5 → 6, `upload-artifact` 4 → 7, `ruff` bumped.

## [0.3.0] - Remote deployment

### Added

- **Streamable HTTP transport.** New `overleaf-mcp serve-http` subcommand exposes the server over HTTP using the MCP SDK's modern Streamable HTTP transport (the one claude.ai web uses). Defaults to `127.0.0.1:8080`; `--host 0.0.0.0` + a reverse proxy gets you public access. Same tool surface, same behavior. Only the wire layer differs from stdio.
- **Mandatory bearer-token auth on the HTTP path.** Server refuses to start without `OVERLEAF_MCP_AUTH_TOKEN` set, because the keychain holds the user's Overleaf tokens and exposing those to an open HTTP port would be wrong. There is no "open mode" flag, even for local testing.
  - Endpoint: `POST /mcp/` (trailing slash required) carrying `Authorization: Bearer <token>`.
  - Token check uses `hmac.compare_digest` so timing on a partial-match attempt doesn't leak the token byte-by-byte.
- **`/healthz` endpoint** returns `{"status": "ok"}` and is exempt from auth so monitoring doesn't need credentials.
- **`core/auth.py`** module with `resolve_auth_token()` and `check_bearer_token()`: transport-agnostic primitives so any future transport (websocket, etc.) reuses the same auth model.

### Notes

- TLS is intentionally out of scope; use a reverse proxy (nginx, caddy, cloudflare) for it. Keeps the server's dep graph small.
- The stdio transport (`overleaf-mcp serve`) is unchanged. Existing Claude Desktop configs keep working.
- Real-socket integration test spins up uvicorn, drives the MCP wire format with the SDK's `streamable_http_client`, and round-trips a tool call through bearer auth: the same code path claude.ai web uses.

## [0.2.0] - Tool surface completion

### Added

- **`get_sections` tool.** Lists every LaTeX section in a `.tex` file with level, line range, and a markdown-style indent so the structure is scannable in Claude's response. Use this before `get_section_content` to discover what's available.
- **`get_section_content` tool.** Returns the body of a named section. Errors loudly when the title isn't found (lists available titles) or matches multiple sections (forces disambiguation rather than silently picking one).
- **`create_file` tool.** Distinct from `edit_file`. Errors with `FileExistsError` if the target already exists, forcing the caller to use `edit_file` for overwrites. Same `pull → validate → write → commit → push` flow.
- **`delete_file` tool.** Pulls latest, removes the file, commits as the system git author, pushes back. Errors if the file doesn't exist (no silent no-ops).
- **`project_status` tool.** One-shot summary: alias + display name, tracked file count, working-tree dirty state, and the last commit (short SHA, author, relative date, subject). Useful for orientation before starting work or for debugging stale-clone situations.
- **`overleaf-mcp project clone <alias>` CLI subcommand.** Replaces the manual `git clone https://git:TOKEN@...` step in setup. Uses the same askpass token-injection as `probe_remote` so the token never lands on the subprocess command line or in the cloned repo's git config. `--force` removes a stale clone and re-clones from scratch. `doctor` now points users at this command instead of suggesting a raw `git clone`.

### Changed

- **`authenticated_git_env` context manager extracted.** The askpass-tempfile pattern previously inlined in `probe_remote` is now a reusable context manager in `core/project.py`. `probe_remote`, the new `clone_with_token` helper, and any future token-authenticated git invocation share the same single implementation. No public API change.

### Internal

- New `GitClient.delete_file(path)` and `GitClient.last_commit_summary()` primitives back the new `delete_file` and `project_status` tools.

## [0.1.2] - Patch release

### Added

- **Non-interactive `init`.**  `overleaf-mcp init` now accepts `--alias`, `--project-id`, `--display-name`, and `--force` flags so the command is fully scriptable.  Passing `--alias` engages non-interactive mode end-to-end: missing required flags fail fast (no silent stdin reads), `--project-id` becomes required, and an existing alias requires `--force` to overwrite (no confirm prompt).  The bare interactive form (`overleaf-mcp init`) is unchanged.
- **Non-interactive `auth add`.**  Two new options for token entry without TTY prompts:
  - `--token-stdin` reads the token from stdin (`printf '%s' "$TOK" | overleaf-mcp auth add ...`).  Recommended for scripts, since it keeps the token off the process command line.
  - `--token-from-env VAR_NAME` reads the token from a named environment variable.  Empty or unset variables fail fast.
  - The two options are mutually exclusive; passing both is a usage error.
  - There is intentionally no `--token VALUE` flag because values on the command line leak via `ps`.

### Notes

- These additions are purely additive. Existing interactive flows and tests keep working unchanged (26 pre-existing CLI tests still pass; 15 new tests cover the flag paths).

## [0.1.1] - Patch release

### Fixed

- `overleaf-mcp --version` no longer crashes with `RuntimeError: 'overleaf_mcp' is not installed`. The CLI now passes `package_name="overleaf-mcp-server"` to click's `version_option`, so the metadata lookup targets the PyPI distribution name rather than the Python module name. All other commands were unaffected by the bug.

### Planned for v0.2

- `get_sections` and `get_section_content` tools using the existing `SectionParser` interface
- `create_file` and `delete_file` tools
- `project_status` tool (file count, last sync, dirty state)
- HTTP/SSE transport for remote / multi-client setups
- A `project clone` CLI subcommand to remove the manual `git clone` step in setup

## [0.1.0] - Initial release

### Added

- Five MCP tools: `list_projects`, `list_files`, `read_file`, `edit_file`, `sync`
- stdio transport with three equivalent entry points (`overleaf-mcp serve`, `python -m overleaf_mcp`, library `build_server()`)
- CLI commands for setup: `init`, `auth add` / `auth remove` / `auth list`, `doctor`
- Token storage in the OS keychain via `keyring` (macOS Keychain, Windows Credential Manager, libsecret on Linux), with environment-variable fallbacks (`OVERLEAF_TOKEN_<ALIAS>`, `OVERLEAF_TOKEN`)
- Configuration file at `~/.config/overleaf-mcp/config.toml` (overridable via `OVERLEAF_MCP_CONFIG`)
- Local clone cache at `~/.cache/overleaf-mcp/<alias>` (overridable via `OVERLEAF_MCP_CACHE`)
- Regex-based LaTeX section parser behind an abstract `SectionParser` interface
- 100% line and branch test coverage on the core and tools layers; an end-to-end integration test exercising the real MCP wire format
