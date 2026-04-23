from pathlib import Path

import pytest
from click.testing import CliRunner

from overleaf_mcp.cli.main import cli
from overleaf_mcp.core.config import load_config


def test_init_creates_new_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="hicss\nproj123\nHICSS 2027\n")
    assert result.exit_code == 0
    assert "Configured 'hicss'" in result.output

    configs = load_config(path)
    assert configs["hicss"].project_id == "proj123"
    assert configs["hicss"].display_name == "HICSS 2027"


def test_init_optional_display_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="foo\nproj\n\n")
    assert result.exit_code == 0
    assert load_config(path)["foo"].display_name is None


def test_init_appends_to_existing_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[projects.existing]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="new\ndef\n\n")
    assert result.exit_code == 0
    configs = load_config(path)
    assert set(configs) == {"existing", "new"}


def test_init_overwrite_confirmed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[projects.hicss]\nproject_id = "old"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="hicss\ny\nnewid\n\n")
    assert result.exit_code == 0
    assert load_config(path)["hicss"].project_id == "newid"


def test_init_overwrite_declined_aborts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[projects.hicss]\nproject_id = "old"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="hicss\nn\n")
    assert result.exit_code != 0
    assert load_config(path)["hicss"].project_id == "old"


def test_init_rejects_empty_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="   \n")
    assert result.exit_code != 0
    assert "alias cannot be empty" in result.output
