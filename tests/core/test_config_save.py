from pathlib import Path

from overleaf_mcp.core.config import ProjectConfig, load_config, save_config


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    original = {
        "hicss": ProjectConfig(alias="hicss", project_id="abc", display_name="HICSS"),
        "mba": ProjectConfig(alias="mba", project_id="def"),
    }
    path = tmp_path / "config.toml"
    save_config(path, original)
    loaded = load_config(path)
    assert loaded == original


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deeper" / "config.toml"
    save_config(path, {"x": ProjectConfig(alias="x", project_id="y")})
    assert path.exists()


def test_save_empty_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    save_config(path, {})
    assert load_config(path) == {}
