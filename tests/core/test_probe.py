import subprocess
from pathlib import Path

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


def test_probe_env_setup_and_askpass_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """The token must be passed via env vars read by a real askpass script,
    not via URL embedding or via the broken GIT_ASKPASS=echo pattern."""
    captured: dict = {}

    def fake_run(
        args: list[str], *, env: dict[str, str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured["env"] = env
        captured["script_path"] = Path(env["GIT_ASKPASS"])
        captured["script_content"] = captured["script_path"].read_text()
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)

    assert probe_remote("proj123", "my-secret-token") is True

    assert captured["args"] == ["git", "ls-remote", "https://git.overleaf.com/proj123"]
    assert captured["env"]["GIT_USERNAME"] == "git"
    assert captured["env"]["GIT_PASSWORD"] == "my-secret-token"
    assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert "GIT_USERNAME" in captured["script_content"]
    assert "GIT_PASSWORD" in captured["script_content"]
    assert not captured["script_path"].exists(), "askpass script should be cleaned up"


def test_probe_cleans_up_askpass_script_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    leaked: list[Path] = []

    def fake_run(
        args: list[str], *, env: dict[str, str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        leaked.append(Path(env["GIT_ASKPASS"]))
        raise subprocess.CalledProcessError(128, args, stderr="auth failed")

    monkeypatch.setattr("overleaf_mcp.core.project.subprocess.run", fake_run)

    assert probe_remote("proj", "tok") is False
    assert leaked and not leaked[0].exists()


def test_askpass_script_returns_username_when_prompted(tmp_path: Path) -> None:
    """Invoke the askpass script the same way git would and assert it returns
    the configured username.

    This guards the class of bug that shipped in v0.1.0: env vars were set
    but the askpass mechanism wasn't actually reading them, so the token
    never reached git. A test that only checks env-var presence wouldn't
    have caught that — the script behavior matters."""
    from overleaf_mcp.core.project import _ASKPASS_SCRIPT

    script_path = tmp_path / "askpass.sh"
    script_path.write_text(_ASKPASS_SCRIPT)
    script_path.chmod(0o700)

    result = subprocess.run(
        [str(script_path), "Username for 'https://git.overleaf.com': "],
        env={"GIT_USERNAME": "git", "GIT_PASSWORD": "secret"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "git"


def test_askpass_script_returns_password_when_prompted(tmp_path: Path) -> None:
    from overleaf_mcp.core.project import _ASKPASS_SCRIPT

    script_path = tmp_path / "askpass.sh"
    script_path.write_text(_ASKPASS_SCRIPT)
    script_path.chmod(0o700)

    result = subprocess.run(
        [str(script_path), "Password for 'https://git@git.overleaf.com': "],
        env={"GIT_USERNAME": "git", "GIT_PASSWORD": "my-token"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "my-token"


def test_askpass_script_handles_lowercase_prompts(tmp_path: Path) -> None:
    """Some git versions / locales emit lowercase prompts. The case-insensitive
    pattern in the script should handle both."""
    from overleaf_mcp.core.project import _ASKPASS_SCRIPT

    script_path = tmp_path / "askpass.sh"
    script_path.write_text(_ASKPASS_SCRIPT)
    script_path.chmod(0o700)

    for prompt, expected in [
        ("username for foo: ", "git"),
        ("password for bar: ", "tok"),
    ]:
        result = subprocess.run(
            [str(script_path), prompt],
            env={"GIT_USERNAME": "git", "GIT_PASSWORD": "tok"},
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout == expected, f"prompt={prompt!r}"
