from pathlib import Path

import pytest
from click.testing import CliRunner

from overleaf_mcp.cli.main import cli
from overleaf_mcp.core.credentials import store_token
from overleaf_mcp.core.errors import GitOperationError


def _config(tmp_path: Path, body: str) -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text(body)
    return cfg


def test_project_clone_succeeds(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc123"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path / "cache"))
    store_token("hicss", "tok")

    captured: list[tuple[str, str, Path]] = []

    def fake_clone(project_id: str, token: str, dest: Path, **_: object) -> None:
        captured.append((project_id, token, dest))
        dest.mkdir(parents=True)

    monkeypatch.setattr("overleaf_mcp.cli.project.clone_with_token", fake_clone)

    result = CliRunner().invoke(cli, ["project", "clone", "hicss"])
    assert result.exit_code == 0, result.output
    assert "Cloned 'hicss'" in result.output
    assert captured == [("abc123", "tok", tmp_path / "cache" / "hicss")]


def test_project_clone_already_exists_no_force(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    cache = tmp_path / "cache"
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(cache))
    (cache / "hicss").mkdir(parents=True)

    monkeypatch.setattr(
        "overleaf_mcp.cli.project.clone_with_token",
        lambda *a, **k: pytest.fail("should not have re-cloned"),
    )

    result = CliRunner().invoke(cli, ["project", "clone", "hicss"])
    assert result.exit_code == 0
    assert "Already cloned" in result.output
    assert "--force" in result.output


def test_project_clone_force_replaces_existing(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    cache = tmp_path / "cache"
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(cache))
    (cache / "hicss").mkdir(parents=True)
    (cache / "hicss" / "stale.txt").write_text("old")
    store_token("hicss", "tok")

    def fake_clone(project_id: str, token: str, dest: Path, **_: object) -> None:
        # Stale dir must be gone when clone is invoked.
        assert not dest.exists(), "old clone should have been removed before re-clone"
        dest.mkdir(parents=True)

    monkeypatch.setattr("overleaf_mcp.cli.project.clone_with_token", fake_clone)

    result = CliRunner().invoke(cli, ["project", "clone", "hicss", "--force"])
    assert result.exit_code == 0
    assert "Cloned 'hicss'" in result.output
    assert not (cache / "hicss" / "stale.txt").exists()


def test_project_clone_unknown_alias(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))

    result = CliRunner().invoke(cli, ["project", "clone", "ghost"])
    assert result.exit_code != 0
    assert "unknown project alias" in result.output


def test_project_clone_no_config(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "missing.toml"))

    result = CliRunner().invoke(cli, ["project", "clone", "hicss"])
    assert result.exit_code != 0
    assert "no config file" in result.output


def test_project_clone_missing_token(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path / "cache"))

    result = CliRunner().invoke(cli, ["project", "clone", "hicss"])
    assert result.exit_code != 0
    assert "no Overleaf token" in result.output


def test_project_clone_git_failure(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path / "cache"))
    store_token("hicss", "bad-tok")

    def boom(*a: object, **k: object) -> None:
        raise GitOperationError("git clone failed: fatal: authentication failed")

    monkeypatch.setattr("overleaf_mcp.cli.project.clone_with_token", boom)

    result = CliRunner().invoke(cli, ["project", "clone", "hicss"])
    assert result.exit_code != 0
    assert "authentication failed" in result.output
