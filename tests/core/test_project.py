import subprocess
from pathlib import Path

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.errors import GitOperationError
from overleaf_mcp.core.project import (
    DEFAULT_CACHE_ROOT,
    authenticated_git_env,
    clone_with_token,
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
    with pytest.raises(RuntimeError, match="git config user.name is not set"):
        get_git_author()


def test_get_git_author_empty_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout="\n", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match="is not set"):
        get_git_author()


def test_authenticated_git_env_yields_correct_env_and_cleans_up_script() -> None:
    """The context manager owns the askpass tempfile lifecycle: chmod 700
    while in scope, unlinked when the with-block exits."""
    with authenticated_git_env("secret-token") as env:
        assert env["GIT_USERNAME"] == "git"
        assert env["GIT_PASSWORD"] == "secret-token"
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        script = Path(env["GIT_ASKPASS"])
        assert script.exists()
        # Script content actually references the env vars (executable)
        assert "GIT_USERNAME" in script.read_text()
        assert "GIT_PASSWORD" in script.read_text()
    # Outside the with-block, the script must be gone.
    assert not script.exists()


def test_clone_with_token_invokes_git_clone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict = {}

    def fake_run(
        args: list[str], *, env: dict[str, str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["env"] = env
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    dest = tmp_path / "nested" / "clone"
    clone_with_token("proj-id-123", "tok", dest)

    assert captured["args"] == ["git", "clone", "https://git.overleaf.com/proj-id-123", str(dest)]
    assert captured["env"]["GIT_USERNAME"] == "git"
    assert captured["env"]["GIT_PASSWORD"] == "tok"
    # Parents created as a side effect, not by the test
    assert dest.parent.exists()


def test_clone_with_token_raises_git_operation_error_on_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(
        args: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(128, args, stderr="fatal: repository not found")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    with pytest.raises(GitOperationError, match="repository not found"):
        clone_with_token("bad-id", "tok", tmp_path / "dest")


def test_clone_with_token_raises_git_operation_error_on_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, 10)

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    with pytest.raises(GitOperationError, match="timed out"):
        clone_with_token("p", "t", tmp_path / "d", timeout=10)
