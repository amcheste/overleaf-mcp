# Acceptance test suite

End-to-end tests against a real Overleaf project. These verify the full
wire path — clone, edit, push, re-clone, assert — that no amount of
mocking can prove. They gate `v*.*.*` releases (see `release.yml`) and
run nightly as a canary against upstream changes (see `nightly.yml`).

## Running locally

You need the same secrets the CI uses:

```sh
export OVERLEAF_TEST_PROJECT_ID=<your-test-project-id>
export OVERLEAF_TEST_TOKEN=<project-scoped-overleaf-token>

uv run pytest tests/acceptance/ -v
```

Without the env vars, every test in the suite skips with a clear
reason — safe to run accidentally.

**Use a dedicated test project**, not anything you actually care about.
Tests mutate the project (writing files under `acceptance/<session-id>/`,
cleaning up on teardown).

## How tests are scoped

Each test session creates a unique directory inside the test project at
`acceptance/<unix-timestamp>-<random>/`. All test files for the run
land under that path. A session-scoped autouse fixture deletes the
whole directory on teardown — single cleanup commit at the end
regardless of how many tests wrote things.

Concurrency: the CI workflows that run this suite share a
`concurrency.group: overleaf-real-ci` so two runs don't fight over the
same git remote. Within a single run, tests share one local clone of
the test project; pytest serializes by default (no xdist).

## Adding a test

A typical write test follows this shape:

```python
from pathlib import Path
import pytest

from overleaf_mcp.core.git_client import GitClient

from .conftest import ACCEPTANCE_AUTHOR


def test_my_new_scenario(
    work_clone: tuple[Path, GitClient],
    fresh_verify_clone_factory,
    acceptance_path: Path,
) -> None:
    work, gc = work_clone

    # 1. Do the action
    target = work / acceptance_path / "thing.tex"
    gc.write_file(target, "expected content")
    gc.commit("acceptance: my scenario", author=ACCEPTANCE_AUTHOR)
    gc.push()

    # 2. Verify by re-cloning fresh — proves the push reached Overleaf
    verify = fresh_verify_clone_factory()
    assert (verify / acceptance_path / "thing.tex").read_text() == "expected content"
```

Two patterns to follow:

- **Use `acceptance_path` for any file you create.** It's a per-test
  unique relative path under `session_dir`, so tests don't collide
  with each other or with prior session runs.
- **Use `fresh_verify_clone` (singular) or `fresh_verify_clone_factory`
  to prove writes landed.** Reading from `work_clone` only proves your
  local change happened, not that Overleaf accepted the push. Always
  re-clone for the assertion.

## What does NOT belong here

Acceptance tests verify *integration with Overleaf*. Things that don't
need a real Overleaf round-trip belong in `tests/core/`,
`tests/tools/`, or `tests/cli/`:

- Pure validation logic (path escape, alias resolution) — unit tests
- Tool-handler call sequences with mocked GitClient — tool tests
- CLI argument parsing and prompts — CLI tests
- The MCP wire protocol itself — `tests/test_*_integration.py`

Adding an acceptance test costs ~15s of CI time per run and one
commit's worth of git history on the test project. The bar is "this
catches a class of regression we can't catch any other way."
