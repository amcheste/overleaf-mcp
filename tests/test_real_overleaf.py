"""End-to-end integration test against a real Overleaf project.

Runs only when both secrets are present:

    OVERLEAF_TEST_PROJECT_ID — project ID of a throwaway Overleaf project
                               dedicated to CI (the test mutates it)
    OVERLEAF_TEST_TOKEN      — project-scoped Overleaf Git token

Skipped automatically on forks, local dev environments without the
secrets, or anywhere the env vars are unset. The CI job that wraps
this test uses ``concurrency.group`` to serialize runs against the
shared remote — see ``.github/workflows/tests.yml``.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from overleaf_mcp.core.git_client import GitClient


PROJECT_ID = os.environ.get("OVERLEAF_TEST_PROJECT_ID")
TOKEN = os.environ.get("OVERLEAF_TEST_TOKEN")


pytestmark = pytest.mark.skipif(
    not (PROJECT_ID and TOKEN),
    reason="real-Overleaf test requires OVERLEAF_TEST_PROJECT_ID and OVERLEAF_TEST_TOKEN",
)


def _clone_url() -> str:
    """Authenticated URL for a one-shot clone in a tmpdir.

    For ``pull`` / ``push`` after clone, git reuses the URL recorded in
    .git/config — fine here because the working tree itself is in a
    pytest tmpdir that gets cleaned up. For long-lived clones the
    server uses the GIT_ASKPASS mechanism so the token never sits in
    .git/config; that path is covered by ``test_probe.py``.
    """
    return f"https://git:{TOKEN}@git.overleaf.com/{PROJECT_ID}"


def _configure_local_identity(repo: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "ci@overleaf-mcp.test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "overleaf-mcp CI"],
        check=True,
        capture_output=True,
    )


def test_real_overleaf_round_trip(tmp_path: Path) -> None:
    """Full server flow against the real remote: clone, pull, write,
    commit, push, then re-clone fresh and verify the change landed.

    A single test on purpose. We don't unit-test against real Overleaf —
    the unit tests already cover every branch with a local bare repo.
    What this proves is the *integration*: that ``git push`` against
    git.overleaf.com actually accepts our commit and the change is
    visible to a fresh clone.
    """
    work = tmp_path / "work"
    GitClient.clone(_clone_url(), work)
    _configure_local_identity(work)

    gc = GitClient(work)
    gc.pull()  # mirrors edit_file's pre-flight

    # Marker is unique per CI run so we can prove THIS commit landed,
    # not just that some past commit did. Locally (no GITHUB_RUN_ID)
    # a uuid keeps the value distinct across reruns.
    run_id = os.environ.get("GITHUB_RUN_ID") or f"local-{uuid.uuid4().hex[:8]}"
    marker = f"run_id={run_id}\ntimestamp={int(time.time())}\n"

    target = work / "ci-marker.txt"
    gc.write_file(target, marker)
    gc.commit(
        message=f"ci: real-overleaf round-trip {run_id}",
        author="overleaf-mcp CI <ci@overleaf-mcp.test>",
    )
    gc.push()

    # Independent verification: clone again from scratch into a different
    # directory and read the marker. If the push didn't actually reach
    # Overleaf the second clone won't have it.
    verify = tmp_path / "verify"
    GitClient.clone(_clone_url(), verify)
    assert (verify / "ci-marker.txt").read_text() == marker, (
        "ci-marker.txt didn't round-trip through Overleaf — push appeared to "
        "succeed but a fresh clone doesn't see the change"
    )
