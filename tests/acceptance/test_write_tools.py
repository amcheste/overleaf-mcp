"""End-to-end tests for write tools against a real Overleaf project.

Each test follows the same load-bearing pattern: do the action via the
tool handler, then re-clone the project from scratch and assert the
change is visible to the fresh clone. Re-cloning is the only way to
prove the push reached Overleaf and isn't just a successful local
commit.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import create_file, delete_file, edit_file


pytestmark = pytest.mark.acceptance


def test_create_file_lands_in_overleaf(
    work_clone: tuple[Path, GitClient],
    fresh_verify_clone: Path,
    acceptance_path: Path,
    project_alias: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create_file via the tool handler → fresh clone sees the file
    with the right content. The full edit_file flow under test:
    pull → validate → write → commit → push, then verify."""
    work, _gc = work_clone

    # Tool handler reads git author from system config; tests overload
    # via monkeypatch on the function it actually imports, not on the
    # core helper.
    monkeypatch.setattr(
        "overleaf_mcp.tools.create_file.get_git_author",
        lambda: "overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )

    target_rel = acceptance_path / "created.tex"
    target_str = str(target_rel)
    expected = "% created via the create_file tool\n"

    asyncio.run(
        create_file.handle(
            {
                "project": project_alias,
                "file_path": target_str,
                "content": expected,
            }
        )
    )

    # Re-clone fresh — must see the new file with the right content.
    landed = (fresh_verify_clone / target_rel).read_text()
    assert landed == expected


def test_create_file_rejects_when_target_exists(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict-create semantics: error before writing if the file is
    already on Overleaf. Verified through the tool handler so we know
    the existence check sees the post-pull state."""
    work, gc = work_clone

    # Pre-create the file via GitClient so it's on Overleaf
    target_rel = acceptance_path / "already_exists.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, "preexisting\n")
    gc.commit(
        f"acceptance: pre-create for create_file rejection test {target_rel}",
        author="overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )
    gc.push()

    monkeypatch.setattr(
        "overleaf_mcp.tools.create_file.get_git_author",
        lambda: "overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )

    with pytest.raises(FileExistsError, match="use edit_file"):
        asyncio.run(
            create_file.handle(
                {
                    "project": project_alias,
                    "file_path": str(target_rel),
                    "content": "would clobber",
                }
            )
        )


def test_edit_file_lands_in_overleaf(
    work_clone: tuple[Path, GitClient],
    fresh_verify_clone: Path,
    acceptance_path: Path,
    project_alias: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """edit_file overwrites a previously-pushed file; verify the new
    content reaches Overleaf and the old content is gone."""
    work, gc = work_clone

    target_rel = acceptance_path / "to_edit.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, "original line\n")
    gc.commit(
        f"acceptance: seed for edit_file test {target_rel}",
        author="overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )
    gc.push()

    monkeypatch.setattr(
        "overleaf_mcp.tools.edit_file.get_git_author",
        lambda: "overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )

    new_content = "rewritten line\nplus a second line\n"
    asyncio.run(
        edit_file.handle(
            {
                "project": project_alias,
                "file_path": str(target_rel),
                "content": new_content,
            }
        )
    )

    landed = (fresh_verify_clone / target_rel).read_text()
    assert landed == new_content


def test_edit_file_short_circuits_on_identical_content(
    work_clone: tuple[Path, GitClient],
    acceptance_path: Path,
    project_alias: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No-op edit doesn't create an empty commit. The handler returns
    'No changes' and the second push produces no new commit on top."""
    work, gc = work_clone

    target_rel = acceptance_path / "no_op_edit.tex"
    target_abs = work / target_rel
    seed = "seed content for no-op edit\n"
    gc.write_file(target_abs, seed)
    gc.commit(
        f"acceptance: seed for no-op edit {target_rel}",
        author="overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )
    gc.push()

    head_before = gc.current_head()

    monkeypatch.setattr(
        "overleaf_mcp.tools.edit_file.get_git_author",
        lambda: "overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )

    result = asyncio.run(
        edit_file.handle(
            {
                "project": project_alias,
                "file_path": str(target_rel),
                "content": seed,  # identical to what's already there
            }
        )
    )
    assert "No changes" in result[0].text

    # HEAD didn't move — short-circuit prevented an empty commit.
    assert gc.current_head() == head_before


def test_delete_file_removes_from_overleaf(
    work_clone: tuple[Path, GitClient],
    fresh_verify_clone: Path,
    acceptance_path: Path,
    project_alias: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """delete_file removes the file from Overleaf — verify with a fresh
    clone that the file is gone."""
    work, gc = work_clone

    target_rel = acceptance_path / "doomed.tex"
    target_abs = work / target_rel
    gc.write_file(target_abs, "soon to be deleted\n")
    gc.commit(
        f"acceptance: seed for delete_file test {target_rel}",
        author="overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )
    gc.push()

    monkeypatch.setattr(
        "overleaf_mcp.tools.delete_file.get_git_author",
        lambda: "overleaf-mcp acceptance <ci@overleaf-mcp.test>",
    )

    asyncio.run(
        delete_file.handle(
            {"project": project_alias, "file_path": str(target_rel)}
        )
    )

    assert not (fresh_verify_clone / target_rel).exists()
