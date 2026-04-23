from pathlib import Path

import pytest
from click.testing import CliRunner

from overleaf_mcp.cli.main import cli
from overleaf_mcp.core.credentials import has_token, store_token


def _write_config(path: Path, body: str) -> Path:
    path.write_text(body)
    return path


def test_auth_add_stores_account_level(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "config.toml"))
    result = CliRunner().invoke(cli, ["auth", "add"], input="my-token\n")
    assert result.exit_code == 0
    assert "account-level fallback" in result.output
    assert has_token(None) is True
    assert has_token("anything") is False


def test_auth_add_with_project_probes_remote(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "config.toml"
    _write_config(cfg, '[projects.hicss]\nproject_id = "proj123"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))

    probe_calls: list[tuple[str, str]] = []

    def fake_probe(project_id: str, token: str, **_: object) -> bool:
        probe_calls.append((project_id, token))
        return True

    monkeypatch.setattr("overleaf_mcp.cli.auth.probe_remote", fake_probe)

    result = CliRunner().invoke(
        cli, ["auth", "add", "--project", "hicss"], input="tok\n"
    )
    assert result.exit_code == 0
    assert probe_calls == [("proj123", "tok")]
    assert "Verified against project 'hicss'" in result.output
    assert has_token("hicss") is True


def test_auth_add_probe_failure_warns_but_stores(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "config.toml"
    _write_config(cfg, '[projects.hicss]\nproject_id = "proj123"\n')
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    monkeypatch.setattr("overleaf_mcp.cli.auth.probe_remote", lambda *a, **k: False)

    result = CliRunner().invoke(
        cli, ["auth", "add", "--project", "hicss"], input="badtok\n"
    )
    assert result.exit_code == 0
    assert "Probe failed" in result.output
    assert has_token("hicss") is True  # Stored even though probe failed


def test_auth_add_project_not_in_config_warns(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "config.toml"))
    result = CliRunner().invoke(
        cli, ["auth", "add", "--project", "ghost"], input="tok\n"
    )
    assert result.exit_code == 0
    assert "not in the config file" in result.output
    assert has_token("ghost") is True


def test_auth_add_rejects_empty_token(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "config.toml"))
    result = CliRunner().invoke(cli, ["auth", "add"], input="   \n")
    assert result.exit_code != 0
    assert has_token(None) is False


def test_auth_remove_when_present(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "config.toml"))
    store_token("hicss", "x")
    result = CliRunner().invoke(cli, ["auth", "remove", "--project", "hicss"])
    assert result.exit_code == 0
    assert "Removed token" in result.output
    assert has_token("hicss") is False


def test_auth_remove_when_absent(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "config.toml"))
    result = CliRunner().invoke(cli, ["auth", "remove"])
    assert result.exit_code == 0
    assert "No token stored" in result.output


def test_auth_list_mixed_state(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _write_config(
        tmp_path / "config.toml",
        '[projects.hicss]\nproject_id = "abc"\n[projects.mba]\nproject_id = "def"\n',
    )
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(cfg))
    store_token(None, "account-tok")
    store_token("hicss", "hicss-tok")

    result = CliRunner().invoke(cli, ["auth", "list"])
    assert result.exit_code == 0
    assert "Account-level fallback: set" in result.output
    assert "Project 'hicss': token set" in result.output
    assert "Project 'mba': no token" in result.output
    # Tokens themselves must not appear
    assert "account-tok" not in result.output
    assert "hicss-tok" not in result.output


def test_auth_list_no_config(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(tmp_path / "config.toml"))
    result = CliRunner().invoke(cli, ["auth", "list"])
    assert result.exit_code == 0
    assert "no projects configured" in result.output
