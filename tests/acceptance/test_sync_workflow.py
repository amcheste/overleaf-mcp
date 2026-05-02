"""End-to-end test for the sync tool.

Models the workflow where Overleaf changes happen outside the MCP
server (e.g. the user edited in the web UI, or another machine pushed)
and the local clone needs to catch up.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import sync

from .conftest import ACCEPTANCE_AUTHOR, _clone_url, _configure_local_identity


pytestmark = pytest.mark.acceptance


def test_sync_pulls_remote_change_made_in_a_separate_clone(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
    tmp_path: Path,
) -> None:
    """Simulate 'someone edited Overleaf in the web UI' by pushing a
    file from a SEPARATE clone, then run sync via the tool handler
    against the work clone — assert the file appears in the work
    clone after sync."""
    work, work_gc = work_clone

    # Make sure work_clone is up to date before we measure HEAD movement
    work_gc.pull()
    head_before = work_gc.current_head()

    # Second clone in a fresh tmp dir — this is the "Overleaf web UI
    # making a change" stand-in.
    other = tmp_path / "other"
    GitClient.clone(_clone_url(), other)
    _configure_local_identity(other)
    other_gc = GitClient(other)

    target_rel = acceptance_path / "from_other_clone.tex"
    other_gc.write_file(other / target_rel, "pushed from a separate clone\n")
    other_gc.commit(
        f"acceptance: external change for sync test {target_rel}",
        author=ACCEPTANCE_AUTHOR,
    )
    other_gc.push()

    # Pre-sync, the work clone hasn't seen the new file
    assert not (work / target_rel).exists()

    # Run sync via the tool handler — should pull and report the move
    result = asyncio.run(sync.handle({"project": project_alias}))
    assert "Synced" in result[0].text
    assert project_alias in result[0].text

    # Post-sync: file is present in the work clone, HEAD has advanced
    assert (work / target_rel).exists()
    assert (work / target_rel).read_text() == "pushed from a separate clone\n"
    assert work_gc.current_head() != head_before


def test_sync_reports_up_to_date_when_nothing_changed(
    work_clone: tuple[Path, GitClient],
    project_alias: str,
) -> None:
    """When the local clone already matches the remote, sync should
    report 'Already up to date' rather than implying a pull happened."""
    _, gc = work_clone
    gc.pull()  # ensure we're current

    result = asyncio.run(sync.handle({"project": project_alias}))
    assert "Already up to date" in result[0].text
