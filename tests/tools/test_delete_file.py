import asyncio
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.errors import PathEscapeError
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import delete_file


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(delete_file, "load_config", lambda _: configs)
    monkeypatch.setattr(delete_file, "get_config_path", lambda: None)
    monkeypatch.setattr(delete_file, "get_git_client", lambda _: gc)
    monkeypatch.setattr(delete_file, "get_git_author", lambda: "T <t@t.test>")


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_delete_file_full_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    (tmp_path / "old.tex").touch()
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(delete_file.handle({"file_path": "old.tex"}))

    expected_path = (tmp_path / "old.tex").resolve()
    assert gc.mock_calls == [
        call.pull(),
        call.delete_file(expected_path),
        call.commit(message="claude: delete old.tex", author="T <t@t.test>"),
        call.push(),
    ]
    assert "Deleted old.tex on hicss" in result[0].text


def test_delete_file_rejects_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(FileNotFoundError, match="does not exist"):
        asyncio.run(delete_file.handle({"file_path": "ghost.tex"}))
    gc.delete_file.assert_not_called()
    gc.commit.assert_not_called()


def test_delete_file_path_escape_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(PathEscapeError):
        asyncio.run(delete_file.handle({"file_path": "../outside"}))
    gc.delete_file.assert_not_called()


def test_delete_file_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(
            delete_file.handle({"file_path": "x.tex", "project": "missing"})
        )
    gc.pull.assert_not_called()
