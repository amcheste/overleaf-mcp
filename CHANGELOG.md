# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The 0.x line signals iteration; the v1.0 API surface will be committed to once the tool list stabilises.

## [Unreleased]

## [0.1.2] - Patch release

### Added

- **Non-interactive `init`.**  `overleaf-mcp init` now accepts `--alias`, `--project-id`, `--display-name`, and `--force` flags so the command is fully scriptable.  Passing `--alias` engages non-interactive mode end-to-end: missing required flags fail fast (no silent stdin reads), `--project-id` becomes required, and an existing alias requires `--force` to overwrite (no confirm prompt).  The bare interactive form (`overleaf-mcp init`) is unchanged.
- **Non-interactive `auth add`.**  Two new options for token entry without TTY prompts:
  - `--token-stdin` reads the token from stdin (`printf '%s' "$TOK" | overleaf-mcp auth add ...`).  Recommended for scripts — keeps the token off the process command line.
  - `--token-from-env VAR_NAME` reads the token from a named environment variable.  Empty or unset variables fail fast.
  - The two options are mutually exclusive; passing both is a usage error.
  - There is intentionally no `--token VALUE` flag because values on the command line leak via `ps`.

### Notes

- These additions are purely additive — existing interactive flows and tests keep working unchanged (26 pre-existing CLI tests still pass; 15 new tests cover the flag paths).

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
