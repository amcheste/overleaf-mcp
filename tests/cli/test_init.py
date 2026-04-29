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


def test_init_rejects_empty_project_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init"], input="alias\n   \n")
    assert result.exit_code != 0
    assert "project_id cannot be empty" in result.output


# ──────────────────────────────────────────────────────────────────────
# Non-interactive flag paths (added in 0.1.2)
# ──────────────────────────────────────────────────────────────────────


def test_init_non_interactive_with_all_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Passing --alias, --project-id, --display-name skips every prompt."""
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(
        cli,
        [
            "init",
            "--alias", "ewrl-2026",
            "--project-id", "abc123",
            "--display-name", "EWRL 2026",
        ],
    )
    assert result.exit_code == 0
    cfg = load_config(path)["ewrl-2026"]
    assert cfg.project_id == "abc123"
    assert cfg.display_name == "EWRL 2026"


def test_init_non_interactive_without_display_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """--display-name is genuinely optional — minimal flag set works."""
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(
        cli, ["init", "--alias", "x", "--project-id", "p"]
    )
    assert result.exit_code == 0
    assert load_config(path)["x"].display_name is None


def test_init_empty_display_name_clears_field(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Passing --display-name '' explicitly stores no display name."""
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(
        cli,
        ["init", "--alias", "x", "--project-id", "p", "--display-name", ""],
    )
    assert result.exit_code == 0
    assert load_config(path)["x"].display_name is None


def test_init_non_interactive_existing_alias_errors_without_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Don't hang on stdin when a script hits a conflict."""
    path = tmp_path / "config.toml"
    path.write_text('[projects.dup]\nproject_id = "old"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(
        cli, ["init", "--alias", "dup", "--project-id", "new"]
    )
    assert result.exit_code != 0
    assert "--force" in result.output
    # Original entry untouched
    assert load_config(path)["dup"].project_id == "old"


def test_init_non_interactive_force_overwrites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[projects.dup]\nproject_id = "old"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(
        cli,
        ["init", "--alias", "dup", "--project-id", "new", "--force"],
    )
    assert result.exit_code == 0
    assert load_config(path)["dup"].project_id == "new"


def test_init_force_with_interactive_prompts_still_overwrites_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """--force suppresses the overwrite prompt even in interactive mode."""
    path = tmp_path / "config.toml"
    path.write_text('[projects.dup]\nproject_id = "old"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    # Interactive — alias provided via prompt, project_id via prompt; the
    # confirm prompt is skipped because --force is set.
    result = CliRunner().invoke(cli, ["init", "--force"], input="dup\nfresh\n\n")
    assert result.exit_code == 0
    assert load_config(path)["dup"].project_id == "fresh"


def test_init_alias_without_project_id_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Passing --alias engages non-interactive mode; --project-id then required.

    Don't fall back to prompts when the user has clearly indicated they're
    scripting — that risks silent stdin consumption from an upstream pipe.
    """
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(cli, ["init", "--alias", "fromflag"])
    assert result.exit_code != 0
    assert "--project-id is required" in result.output


def test_init_non_interactive_rejects_empty_alias_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "config.toml"
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(path))

    result = CliRunner().invoke(
        cli, ["init", "--alias", "   ", "--project-id", "p"]
    )
    assert result.exit_code != 0
    assert "alias cannot be empty" in result.output


def test_serve_invokes_stdio_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []
    monkeypatch.setattr("overleaf_mcp.cli.main._serve_main", lambda: called.append(True))
    result = CliRunner().invoke(cli, ["serve"])
    assert result.exit_code == 0
    assert called == [True]


def test_version_flag_prints_package_version() -> None:
    """Regression test for the v0.1.0 bug where --version crashed because
    click's auto-detection looked up 'overleaf_mcp' (module name) instead
    of 'overleaf-mcp-server' (PyPI distribution name)."""
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()
