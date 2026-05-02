"""Shared infrastructure for the acceptance suite.

Acceptance tests run against a real Overleaf project (configured via
OVERLEAF_TEST_PROJECT_ID and OVERLEAF_TEST_TOKEN). They:

  - Mark themselves so the default ``pytest`` run skips them; CI opts in
    explicitly via ``pytest tests/acceptance/`` or ``pytest -m acceptance``
  - Skip cleanly when the secrets aren't set, so forks / local dev don't
    try to hit a remote they can't authenticate against
  - Confine all writes to ``acceptance/<session-id>/`` so multiple test
    sessions and the user's own work in the test project don't collide
  - Clean up the session's directory at the end of the run, even if
    individual tests failed (cleanup failure logs a warning rather than
    masking the real test failures)

The pattern across most write tests:

  1. Use ``work_clone`` fixture to get a real clone of the test project
  2. Do the action (create/edit/delete via real GitClient or via the
     tool handler, depending on which level the test is exercising)
  3. Use ``fresh_verify_clone`` to clone again from scratch and assert
     the change actually landed on Overleaf — the only way to prove
     the push reached the remote and isn't just a successful local
     commit
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from overleaf_mcp.core.git_client import GitClient


PROJECT_ID = os.environ.get("OVERLEAF_TEST_PROJECT_ID")
TOKEN = os.environ.get("OVERLEAF_TEST_TOKEN")


def _clone_url() -> str:
    return f"https://git:{TOKEN}@git.overleaf.com/{PROJECT_ID}"


def _configure_local_identity(repo: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "ci@overleaf-mcp.test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "overleaf-mcp acceptance"],
        check=True,
        capture_output=True,
    )


# ────────────────────────────────────────────────────────────────────
# Marker + skip-on-no-secrets policy
# ────────────────────────────────────────────────────────────────────

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip every acceptance-marked test when secrets aren't set.

    The marker is applied per-test-file via ``pytestmark = pytest.mark.acceptance``
    rather than auto-applied here, so this hook safely no-ops on items
    collected from outside the acceptance subdirectory.
    """
    if PROJECT_ID and TOKEN:
        return
    skip = pytest.mark.skip(
        reason="acceptance suite requires OVERLEAF_TEST_PROJECT_ID + OVERLEAF_TEST_TOKEN"
    )
    for item in items:
        if "acceptance" in item.keywords:
            item.add_marker(skip)


# ────────────────────────────────────────────────────────────────────
# Session-scoped fixtures: identity, working clone, cleanup
# ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def session_id() -> str:
    """Unique key for this run. Used in test paths so concurrent CI
    runs don't collide on the same file paths inside the test project.
    """
    return f"{int(time.time())}-{uuid.uuid4().hex[:6]}"


# The alias every acceptance test uses to refer to the test project.
PROJECT_ALIAS = "acceptance"


@pytest.fixture(scope="session")
def _acceptance_env(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, GitClient]:
    """Session-wide setup that wires the test project under the alias
    ``acceptance`` so every tool handler resolves correctly:

      - Writes a tmp config.toml with one project entry
      - Points OVERLEAF_MCP_CONFIG at it
      - Points OVERLEAF_MCP_CACHE at a tmp dir
      - Clones the test project into ``<cache>/acceptance/`` so
        ``get_git_client("acceptance")`` finds it

    Returns the work directory + GitClient. Tests should ask for the
    public ``work_clone`` fixture instead of this private one.
    """
    tmp = tmp_path_factory.mktemp("acceptance")
    cache_dir = tmp / "cache"
    cache_dir.mkdir()

    config_path = tmp / "config.toml"
    config_path.write_text(
        f'[projects.{PROJECT_ALIAS}]\nproject_id = "{PROJECT_ID}"\n'
    )

    os.environ["OVERLEAF_MCP_CONFIG"] = str(config_path)
    os.environ["OVERLEAF_MCP_CACHE"] = str(cache_dir)

    workdir = cache_dir / PROJECT_ALIAS
    GitClient.clone(_clone_url(), workdir)
    _configure_local_identity(workdir)
    return workdir, GitClient(workdir)


@pytest.fixture(scope="session")
def work_clone(_acceptance_env: tuple[Path, GitClient]) -> tuple[Path, GitClient]:
    """A fresh clone of the test project, valid for the whole session.

    Tests share this clone — the alternative (clone-per-test) would
    triple test runtime against Overleaf's git remote for no real
    isolation benefit, since the tests serialize via the CI
    concurrency group anyway.
    """
    return _acceptance_env


@pytest.fixture(scope="session")
def project_alias() -> str:
    """The configured alias for the test project. Pass this to tool
    handlers' ``project`` argument."""
    return PROJECT_ALIAS


@pytest.fixture
def fresh_verify_clone(tmp_path: Path) -> Path:
    """A fresh clone for proving writes reached Overleaf.

    Use this AFTER a write to verify the change is visible to a clean
    third party — the only way to know the push actually landed and
    isn't just a successful local commit.
    """
    workdir = tmp_path / "verify"
    GitClient.clone(_clone_url(), workdir)
    return workdir


@pytest.fixture(scope="session")
def session_dir(session_id: str) -> Path:
    """The directory under which all test files for this session live.

    Tests should write under this path so the session-end cleanup can
    remove everything in one shot.
    """
    return Path("acceptance") / session_id


@pytest.fixture(scope="session", autouse=True)
def _cleanup_session(
    work_clone: tuple[Path, GitClient],
    session_dir: Path,
    session_id: str,
) -> Iterator[None]:
    """Remove the session's acceptance/<session_id>/ directory on teardown.

    Cleanup failures log a warning rather than raise — we don't want a
    cleanup hiccup to mask real test failures that already ran.
    """
    yield
    work, gc = work_clone
    target = work / session_dir
    if not target.exists():
        return
    try:
        gc.pull()
        shutil.rmtree(target)
        gc.commit(
            f"acceptance: cleanup session {session_id}",
            author="overleaf-mcp acceptance <ci@overleaf-mcp.test>",
        )
        gc.push()
    except Exception as exc:  # noqa: BLE001  — warning only, don't mask test failures
        print(f"\nwarning: acceptance cleanup failed: {exc}", flush=True)


# ────────────────────────────────────────────────────────────────────
# Per-test helper: a unique path inside session_dir
# ────────────────────────────────────────────────────────────────────

@pytest.fixture
def acceptance_path(session_dir: Path, request: pytest.FixtureRequest) -> Path:
    """Return a unique relative path scoped to this test, under
    acceptance/<session_id>/. Each test that writes a file should ask
    for this so paths don't collide across the suite.

    Returns a relative Path like
    ``acceptance/<session_id>/test_create_file_lands_in_overleaf/file.tex``.
    Caller appends the filename.
    """
    return session_dir / request.node.name


# ────────────────────────────────────────────────────────────────────
# Author identity used by every test that commits
# ────────────────────────────────────────────────────────────────────

ACCEPTANCE_AUTHOR = "overleaf-mcp acceptance <ci@overleaf-mcp.test>"
