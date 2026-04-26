import subprocess
from pathlib import Path

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.project import (
    DEFAULT_CACHE_ROOT,
    get_cache_root,
    get_git_author,
    get_git_client,
    get_repo_path,
    resolve_default_alias,
)


def test_cache_root_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OVERLEAF_MCP_CACHE", raising=False)
    assert get_cache_root() == DEFAULT_CACHE_ROOT


def test_cache_root_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path))
    assert get_cache_root() == tmp_path


def test_repo_path_joins_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path))
    assert get_repo_path("hicss") == tmp_path / "hicss"


def test_get_git_client_points_at_repo_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OVERLEAF_MCP_CACHE", str(tmp_path))
    gc = get_git_client("hicss")
    assert gc.repo_path == tmp_path / "hicss"


def test_resolve_default_alias_single_project() -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    assert resolve_default_alias(configs) == "hicss"


def test_resolve_default_alias_empty_raises() -> None:
    with pytest.raises(ValueError, match="no projects"):
        resolve_default_alias({})


def test_resolve_default_alias_multiple_raises() -> None:
    configs = {
        "hicss": ProjectConfig(alias="hicss", project_id="abc"),
        "mba": ProjectConfig(alias="mba", project_id="def"),
    }
    with pytest.raises(ValueError, match="multiple projects"):
        resolve_default_alias(configs)


def test_get_git_author_reads_system_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        key = args[-1]
        value = {"user.name": "Alice", "user.email": "alice@example.com"}[key]
        return subprocess.CompletedProcess(args, 0, stdout=value + "\n", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    assert get_git_author() == "Alice <alice@example.com>"
    assert calls == [
        ["git", "config", "--get", "user.name"],
        ["git", "config", "--get", "user.email"],
    ]


def test_get_git_author_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    with pytest.raises(RuntimeError) as exc_info:
        get_git_author()
    msg = str(exc_info.value)
    assert "git config user.name is not set" in msg
    # The error must give a concrete fix command — not just diagnose.
    assert "git config --global user.name" in msg


def test_get_git_author_empty_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout="\n", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match="is not set"):
        get_git_author()
