from pathlib import Path

import pytest
from click.testing import CliRunner

from overleaf_mcp.cli.main import cli
from overleaf_mcp.core.credentials import store_token
from overleaf_mcp.core.errors import TokenNotFoundError


def _config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body)
    return path


def _healthy_env(
    monkeypatch: pytest.MonkeyPatch,
    config_path: Path,
    probe_returns: bool = True,
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(config_path))
    monkeypatch.setattr(
        "overleaf_mcp.cli.main.get_git_author", lambda: "Test <t@example.com>"
    )
    monkeypatch.setattr(
        "overleaf_mcp.cli.main.probe_remote", lambda *a, **k: probe_returns
    )


def test_doctor_missing_config_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "missing.toml"))
    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "config file does not exist" in result.output


def test_doctor_malformed_config_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text("[projects.foo\nbroken =")
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "could not parse config" in result.output


def test_doctor_all_green(
    fake_keyring: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path / "cache"))
    _healthy_env(monkeypatch, cfg, probe_returns=True)
    store_token("hicss", "tok")
    (tmp_path / "cache" / "hicss").mkdir(parents=True)

    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "loaded 1 project" in result.output
    assert "Token: ok" in result.output
    assert "Remote: ok" in result.output
    assert "Clone: ok" in result.output
    assert "All checks passed" in result.output


def test_doctor_reports_missing_token(
    fake_keyring: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    _healthy_env(monkeypatch, cfg)

    def _no_token(_a: str) -> str:
        raise TokenNotFoundError("missing")

    monkeypatch.setattr("overleaf_mcp.cli.main.resolve_token", _no_token)

    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "Token: FAIL" in result.output
    assert "1 check(s) failed" in result.output


def test_doctor_reports_probe_failure(
    fake_keyring: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    _healthy_env(monkeypatch, cfg, probe_returns=False)
    store_token("hicss", "tok")

    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "Remote: FAIL" in result.output


def test_doctor_reports_missing_clone(
    fake_keyring: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = _config(tmp_path, '[projects.hicss]\nproject_id = "abc"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path / "cache"))
    _healthy_env(monkeypatch, cfg)
    store_token("hicss", "tok")

    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 0  # missing clone is informational, not a failure
    assert "Clone: missing" in result.output


def test_doctor_reports_missing_git_author(
    fake_keyring: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = _config(tmp_path, "# empty\n")
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))

    def _boom() -> str:
        raise RuntimeError("git config user.name is not set")

    monkeypatch.setattr("overleaf_mcp.cli.main.get_git_author", _boom)
    monkeypatch.setattr("overleaf_mcp.cli.main.probe_remote", lambda *a, **k: True)

    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "Git author: FAIL" in result.output


def test_doctor_reports_missing_git_binary(
    fake_keyring: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg = _config(tmp_path, "# empty\n")
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    monkeypatch.setattr(
        "overleaf_mcp.cli.main.get_git_author", lambda: "T <t@t.test>"
    )
    monkeypatch.setattr("overleaf_mcp.cli.main.shutil.which", lambda _: None)

    result = CliRunner().invoke(cli, ["doctor"])
    assert result.exit_code == 1
    assert "Git binary: NOT FOUND" in result.output
