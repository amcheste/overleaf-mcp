# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The 0.x line signals iteration; the v1.0 API surface will be committed to once the tool list stabilises.

## [Unreleased]

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
