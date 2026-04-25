import asyncio
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.errors import PathEscapeError
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import edit_file


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
    author: str = "Tester <tester@example.com>",
) -> None:
    monkeypatch.setattr(edit_file, "load_config", lambda _: configs)
    monkeypatch.setattr(edit_file, "get_config_path", lambda: None)
    monkeypatch.setattr(edit_file, "get_git_client", lambda _: gc)
    monkeypatch.setattr(edit_file, "get_git_author", lambda: author)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    gc.working_tree_dirty.return_value = True
    return gc


def test_happy_path_invokes_full_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(
        edit_file.handle(
            {"file_path": "sections/intro.tex", "content": "new\n"}
        )
    )

    expected_path = (tmp_path / "sections" / "intro.tex").resolve()
    assert gc.mock_calls == [
        call.pull(),
        call.write_file(expected_path, "new\n"),
        call.working_tree_dirty(),
        call.commit(
            message="claude: edit sections/intro.tex",
            author="Tester <tester@example.com>",
        ),
        call.push(),
    ]
    assert "Edited and pushed sections/intro.tex on hicss" in result[0].text


def test_no_changes_short_circuits_commit_and_push(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.working_tree_dirty.return_value = False
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(
        edit_file.handle({"file_path": "x.tex", "content": "same\n"})
    )
    assert "No changes to x.tex" in result[0].text
    gc.commit.assert_not_called()
    gc.push.assert_not_called()


def test_path_escape_rejected_before_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(PathEscapeError):
        asyncio.run(
            edit_file.handle({"file_path": "../outside", "content": "x"})
        )
    gc.write_file.assert_not_called()
    gc.commit.assert_not_called()
    gc.push.assert_not_called()


def test_unknown_alias_rejected_before_git_operations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(
            edit_file.handle(
                {"file_path": "x.tex", "content": "y", "project": "missing"}
            )
        )
    gc.pull.assert_not_called()


def test_git_author_failure_aborts_before_pull(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    monkeypatch.setattr(edit_file, "load_config", lambda _: configs)
    monkeypatch.setattr(edit_file, "get_config_path", lambda: None)
    monkeypatch.setattr(edit_file, "get_git_client", lambda _: gc)

    def _boom() -> str:
        raise RuntimeError("git config user.name is not set")

    monkeypatch.setattr(edit_file, "get_git_author", _boom)

    with pytest.raises(RuntimeError, match="not set"):
        asyncio.run(edit_file.handle({"file_path": "x.tex", "content": "y"}))
    gc.pull.assert_not_called()
