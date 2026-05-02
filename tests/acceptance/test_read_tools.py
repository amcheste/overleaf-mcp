"""End-to-end tests for read-only tools against a real Overleaf project.

Each test calls the actual MCP tool handler (not just the underlying
GitClient) so we exercise the whole stack: input validation → tool
logic → core helpers → real git → real Overleaf.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import (
    get_section_content,
    get_sections,
    list_files,
    list_projects,
    project_status,
    read_file,
)

from .conftest import ACCEPTANCE_AUTHOR


pytestmark = pytest.mark.acceptance


def test_list_projects_returns_acceptance_alias(project_alias: str) -> None:
    """list_projects reads the config — proves config wiring works."""
    result = asyncio.run(list_projects.handle({}))
    assert project_alias in result[0].text


def test_list_files_includes_files_we_just_committed(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
) -> None:
    """Write a file via the local clone, push, then call list_files via
    the tool handler — should see the file we just pushed."""
    work, gc = work_clone

    target_rel = acceptance_path / "list_files_canary.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, "% list_files canary\n")
    gc.commit(
        f"acceptance: list_files canary {target_rel}",
        author=ACCEPTANCE_AUTHOR,
    )
    gc.push()

    result = asyncio.run(list_files.handle({"project": project_alias}))
    assert str(target_rel) in result[0].text


def test_read_file_returns_committed_content(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
) -> None:
    """Push a file, then read it back via the tool handler.

    This is the round-trip equivalent of 'I committed a file in
    Overleaf, can Claude see what's in it?' — except we drove the
    write side ourselves to keep the test deterministic.
    """
    work, gc = work_clone

    expected = "Round-trip read content.\nLine two.\n"
    target_rel = acceptance_path / "read_canary.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, expected)
    gc.commit(
        f"acceptance: read_file canary {target_rel}",
        author=ACCEPTANCE_AUTHOR,
    )
    gc.push()

    result = asyncio.run(
        read_file.handle({"project": project_alias, "file_path": str(target_rel)})
    )
    assert result[0].text == expected


def test_get_sections_against_real_latex_round_trip(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
) -> None:
    """Push a structured .tex file, then list its sections via the tool
    handler. Proves the parser works against real-Overleaf-stored LaTeX,
    not just the synthetic strings in unit tests."""
    work, gc = work_clone

    sample = (
        "\\section{Acceptance Intro}\n"
        "Body of intro.\n"
        "\\subsection{First sub}\n"
        "First sub body.\n"
        "\\section{Acceptance Method}\n"
        "Body of method.\n"
    )
    target_rel = acceptance_path / "structured.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, sample)
    gc.commit(
        f"acceptance: get_sections canary {target_rel}",
        author=ACCEPTANCE_AUTHOR,
    )
    gc.push()

    result = asyncio.run(
        get_sections.handle({"project": project_alias, "file_path": str(target_rel)})
    )
    text = result[0].text
    assert "Acceptance Intro" in text
    assert "First sub" in text
    assert "Acceptance Method" in text


def test_get_section_content_extracts_named_section(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
) -> None:
    work, gc = work_clone

    sample = (
        "\\section{Alpha}\nAlpha body line 1\nAlpha body line 2\n"
        "\\section{Beta}\nBeta body\n"
    )
    target_rel = acceptance_path / "named_sections.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, sample)
    gc.commit(
        f"acceptance: get_section_content canary {target_rel}",
        author=ACCEPTANCE_AUTHOR,
    )
    gc.push()

    result = asyncio.run(
        get_section_content.handle(
            {
                "project": project_alias,
                "file_path": str(target_rel),
                "title": "Alpha",
            }
        )
    )
    body = result[0].text
    assert "Alpha body line 1" in body
    assert "Alpha body line 2" in body
    assert "Beta" not in body  # stops at next section


def test_project_status_returns_state(project_alias: str) -> None:
    """project_status hits multiple GitClient methods (list_files,
    working_tree_dirty, last_commit_summary). Verifies they all work
    against the real clone."""
    result = asyncio.run(project_status.handle({"project": project_alias}))
    text = result[0].text
    assert f"Project: {project_alias}" in text
    assert "Files tracked:" in text
    assert "Working tree dirty:" in text
    assert "Last commit:" in text
