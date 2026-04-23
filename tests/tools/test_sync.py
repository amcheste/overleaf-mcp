import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import sync


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(sync, "load_config", lambda _: configs)
    monkeypatch.setattr(sync, "get_config_path", lambda: None)
    monkeypatch.setattr(sync, "get_git_client", lambda _: gc)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_reports_up_to_date_when_head_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.current_head.side_effect = ["sha1", "sha1"]
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(sync.handle({}))
    assert "Already up to date on hicss" in result[0].text
    gc.pull.assert_called_once()


def test_reports_synced_when_head_advances(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    gc.current_head.side_effect = ["sha1", "sha2"]
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(sync.handle({}))
    assert "Synced hicss" in result[0].text


def test_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(sync.handle({"project": "missing"}))
    gc.pull.assert_not_called()
