import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from overleaf_mcp.core.config import (
    DEFAULT_CONFIG_PATH,
    ProjectConfig,
    get_config_path,
    load_config,
)


def _write_config(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_load_single_project(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path / "config.toml",
        '[projects.hicss]\nproject_id = "abc123"\ndisplay_name = "HICSS 2027"\n',
    )
    result = load_config(cfg)
    assert set(result) == {"hicss"}
    assert result["hicss"] == ProjectConfig(
        alias="hicss", project_id="abc123", display_name="HICSS 2027"
    )


def test_load_multiple_projects(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path / "config.toml",
        '[projects.hicss]\nproject_id = "abc"\n'
        '[projects.mba]\nproject_id = "def"\ndisplay_name = "MBA"\n',
    )
    result = load_config(cfg)
    assert set(result) == {"hicss", "mba"}
    assert result["hicss"].display_name is None
    assert result["mba"].display_name == "MBA"


def test_missing_display_name_allowed(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path / "config.toml", '[projects.foo]\nproject_id = "x"\n')
    assert load_config(cfg)["foo"].display_name is None


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.toml")


def test_empty_projects_section(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path / "config.toml", "# no projects\n")
    assert load_config(cfg) == {}


def test_missing_project_id_rejected(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path / "config.toml", '[projects.foo]\ndisplay_name = "x"\n')
    with pytest.raises(ValidationError):
        load_config(cfg)


def test_invalid_toml_propagates(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path / "config.toml", "[projects.foo\nproject_id =")
    with pytest.raises(tomllib.TOMLDecodeError):
        load_config(cfg)


def test_config_path_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    override = tmp_path / "custom.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(override))
    assert get_config_path() == override


def test_config_path_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OVERLEAF_MCP_CONFIG", raising=False)
    assert get_config_path() == DEFAULT_CONFIG_PATH
