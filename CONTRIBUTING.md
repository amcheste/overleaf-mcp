# Contributing

Thanks for considering a contribution. This file is short on purpose —
the project is small and the conventions are easy.

## Quick start

```sh
git clone https://github.com/amcheste/overleaf-mcp.git
cd overleaf-mcp

# Install dev environment
uv sync --extra dev

# Optional but recommended: install the pre-commit hooks
# (matches what CI checks, catches issues before push)
uv run pre-commit install

# Run the suite
uv run pytest

# Run the linter
uv run ruff check src/ tests/

# Run a single test file or test
uv run pytest tests/core/test_paths.py -v
uv run pytest tests/core/test_paths.py::test_absolute_path_rejected -v

# Acceptance suite (real Overleaf round-trips). Excluded from the default
# run; opt in with -m. Requires OVERLEAF_TEST_PROJECT_ID and
# OVERLEAF_TEST_TOKEN; skips cleanly without them.
uv run pytest -m acceptance -v
```

You'll need Python 3.11 or newer and [`uv`](https://github.com/astral-sh/uv).

### Previewing the docs site locally

The documentation site (https://amcheste.github.io/overleaf-mcp/) is
built with MkDocs Material. To work on it locally:

```sh
uv sync --extra docs
uv run mkdocs serve
# Open http://127.0.0.1:8000 — auto-reloads on changes
```

Build the static site (what CI deploys):

```sh
uv run mkdocs build --strict
# Output goes to site/ which is gitignored
```

The `--strict` flag catches broken links and missing files. CI uses the
same flag, so if it builds locally it'll build in CI.

## Branch model

- **`develop`** is the integration branch. PRs target `develop`.
- **`main`** is the release branch. Promoted from `develop` via CLI
  `--no-ff` merge at release time, never via a GitHub PR.
- Feature branches: `feat/<short-name>`, `fix/<short-name>`,
  `docs/<short-name>`, `test/<short-name>`, `chore/<short-name>`.
- Branch protection requires the `All tests passed` and
  `All wheel-smoke tests passed` aggregator checks before merge to
  either `develop` or `main`.

## Commit messages

Conventional Commits, prefix-only:

- `feat(core): ...` for new functionality
- `fix(tools): ...` for bug fixes
- `docs: ...` for documentation
- `test: ...` for test additions
- `chore: ...` for tooling and release work
- `refactor: ...` for non-behavior-changing structural changes
- `ci: ...` for workflow changes

The body of the commit should explain *why*, not just *what*. The diff
already shows the what.

## What "done" looks like for a PR

Before opening a PR:

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check src/ tests/` is clean
- [ ] Coverage hasn't dropped (visible in pytest output; the bar is
      80% but we hold 100% on the measured modules)
- [ ] If you added user-visible behavior, the README or CHANGELOG
      reflects it
- [ ] Pre-commit ran on every commit (or you ran `uv run ruff format`
      manually)

Acceptance tests (`uv run pytest -m acceptance`) gate **releases**, not
PRs — so you don't need them to run them on every PR. They run on
every `v*.*.*` tag push (blocking PyPI publish if any fail) and once
nightly (opening an issue if anything breaks). See
[`tests/acceptance/README.md`](https://github.com/amcheste/overleaf-mcp/blob/main/tests/acceptance/README.md)
for what's covered and how to add to the suite.

## Code style

- **Default to no comments.** The code should explain itself; comments
  exist to document *why* a non-obvious decision was made, not to
  narrate *what* a line does.
- **Test the behaviour, not the implementation.** Mocks at module
  boundaries; real subprocess + real git in `tests/core/test_git_client.py`.
- **Prefer named exceptions over generic ones** for things callers
  might reasonably want to handle differently (`PathEscapeError`,
  `TokenNotFoundError`, `GitOperationError`).
- **Error messages are UX.** Include the actionable next step when you
  can — error messages are the first thing users read when something
  fails.

## Architecture overview

See [CLAUDE.md](https://github.com/amcheste/overleaf-mcp/blob/main/CLAUDE.md)
for the in-repo design notes — what each subpackage owns, why git is the
write API, why credentials never touch disk, why the server is
single-process / single-user by design. That file is the one-stop
overview for understanding the codebase.

## Where to ask questions

- **Bug?** [File an issue](https://github.com/amcheste/overleaf-mcp/issues/new?template=bug_report.yml)
- **Idea?** [File a feature request](https://github.com/amcheste/overleaf-mcp/issues/new?template=feature_request.yml)
- **General question?** [GitHub Discussions](https://github.com/amcheste/overleaf-mcp/discussions)
- **Security issue?** Please report privately — see [SECURITY.md](https://github.com/amcheste/overleaf-mcp/blob/main/SECURITY.md)
