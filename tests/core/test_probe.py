import subprocess

import pytest

from overleaf_mcp.core.project import probe_remote


def test_probe_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args[:2] == ["git", "ls-remote"]
        assert "git.overleaf.com/proj123" in args[2]
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    assert probe_remote("proj123", "tok") is True


def test_probe_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(128, args, stderr="auth failed")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    assert probe_remote("proj123", "bad-token") is False


def test_probe_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, 10)

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    assert probe_remote("proj", "tok", timeout=0.1) is False


def test_probe_git_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("git")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)
    assert probe_remote("proj", "tok") is False
