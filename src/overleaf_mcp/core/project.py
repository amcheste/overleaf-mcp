import os
import subprocess
from pathlib import Path

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.git_client import GitClient


DEFAULT_CACHE_ROOT = Path.home() / ".cache" / "overleaf-mcp"


def get_cache_root() -> Path:
    """Return the cache root from OVERLEAF_MCP_CACHE env var, or the default."""
    override = os.environ.get("OVERLEAF_MCP_CACHE")
    return Path(override) if override else DEFAULT_CACHE_ROOT


def get_repo_path(alias: str) -> Path:
    return get_cache_root() / alias


def get_git_client(alias: str) -> GitClient:
    return GitClient(get_repo_path(alias))


def resolve_default_alias(configs: dict[str, ProjectConfig]) -> str:
    """Pick an alias when the caller didn't specify one.

    If exactly one project is configured, use it. Otherwise raise with a
    clear message instructing the caller to pass an explicit alias.
    """
    if not configs:
        raise ValueError("no projects configured")
    if len(configs) == 1:
        return next(iter(configs))
    raise ValueError(
        f"multiple projects configured ({', '.join(sorted(configs))}); "
        f"specify one with the 'project' argument"
    )


def get_git_author() -> str:
    """Read author identity from system git config as 'Name <email>'."""
    name = _git_config("user.name")
    email = _git_config("user.email")
    return f"{name} <{email}>"


def _git_config(key: str) -> str:
    result = subprocess.run(
        ["git", "config", "--get", key],
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        raise RuntimeError(
            f"git config {key} is not set. Run "
            f"'git config --global {key} <value>' to configure it."
        )
    return value



def probe_remote(project_id: str, token: str, timeout: float = 10.0) -> bool:
    """Check whether a token can reach an Overleaf project's git remote.

    Uses 'git ls-remote' which reads refs without cloning. Returns True on
    success, False on any failure (auth, network, timeout). Never raises.
    """
    url = f"https://git.overleaf.com/{project_id}"
    env = os.environ.copy()
    env["GIT_ASKPASS"] = "echo"
    env["GIT_USERNAME"] = "git"
    env["GIT_PASSWORD"] = token
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        subprocess.run(
            ["git", "ls-remote", url],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False

