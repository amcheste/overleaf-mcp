import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import list_files


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(list_files, "load_config", lambda _: configs)
    monkeypatch.setattr(list_files, "get_config_path", lambda: None)
    monkeypatch.setattr(list_files, "get_git_client", lambda _: gc)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_lists_files_with_explicit_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.list_files.return_value = [tmp_path / "intro.tex", tmp_path / "methods.tex"]
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(list_files.handle({"project": "hicss"}))
    assert result[0].text == "intro.tex\nmethods.tex"
    gc.list_files.assert_called_once_with(extension=None)


def test_lists_files_with_default_project_when_single(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.list_files.return_value = [tmp_path / "a.tex"]
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(list_files.handle({}))
    assert result[0].text == "a.tex"


def test_extension_filter_passed_through(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.list_files.return_value = []
    _patch(monkeypatch, configs, gc)

    asyncio.run(list_files.handle({"extension": "tex"}))
    gc.list_files.assert_called_once_with(extension="tex")


def test_empty_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.list_files.return_value = []
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(list_files.handle({}))
    assert "no tracked files" in result[0].text


def test_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(list_files.handle({"project": "missing"}))
