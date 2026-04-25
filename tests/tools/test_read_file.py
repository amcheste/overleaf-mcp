import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.errors import PathEscapeError
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import read_file


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(read_file, "load_config", lambda _: configs)
    monkeypatch.setattr(read_file, "get_config_path", lambda: None)
    monkeypatch.setattr(read_file, "get_git_client", lambda _: gc)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_reads_file_contents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    (tmp_path / "intro.tex").touch()
    gc.read_file.return_value = "\\section{Intro}\n"
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(read_file.handle({"file_path": "intro.tex"}))
    assert result[0].text == "\\section{Intro}\n"
    gc.read_file.assert_called_once_with((tmp_path / "intro.tex").resolve())


def test_path_escape_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(PathEscapeError):
        asyncio.run(read_file.handle({"file_path": "../etc/passwd"}))
    gc.read_file.assert_not_called()


def test_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(read_file.handle({"file_path": "x.tex", "project": "nope"}))


def test_missing_file_path_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        asyncio.run(read_file.handle({}))
