import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import project_status


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(project_status, "load_config", lambda _: configs)
    monkeypatch.setattr(project_status, "get_config_path", lambda: None)
    monkeypatch.setattr(project_status, "get_git_client", lambda _: gc)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_status_clean_with_display_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {
        "hicss": ProjectConfig(
            alias="hicss", project_id="abc", display_name="HICSS 2027"
        )
    }
    gc = _fake_gc(tmp_path)
    gc.list_files.return_value = [tmp_path / "a.tex", tmp_path / "b.tex"]
    gc.working_tree_dirty.return_value = False
    gc.last_commit_summary.return_value = "abc1234 Alan <alan@example.com> (2 hours ago)\nadd intro section"
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(project_status.handle({}))
    text = result[0].text
    assert "Project: hicss (HICSS 2027)" in text
    assert "Files tracked: 2" in text
    assert "Working tree dirty: no" in text
    assert "abc1234 Alan" in text
    assert "add intro section" in text


def test_status_dirty_without_display_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"plain": ProjectConfig(alias="plain", project_id="x")}
    gc = _fake_gc(tmp_path)
    gc.list_files.return_value = []
    gc.working_tree_dirty.return_value = True
    gc.last_commit_summary.return_value = "0000000 - (just now)\ninitial"
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(project_status.handle({}))
    text = result[0].text
    assert "Project: plain" in text
    assert "(" not in text.splitlines()[0]  # no display-name parens on first line
    assert "Files tracked: 0" in text
    assert "Working tree dirty: yes" in text


def test_status_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(project_status.handle({"project": "missing"}))
