import os
import tomllib
from pathlib import Path

from pydantic import BaseModel


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "overleaf-mcp" / "config.toml"


class ProjectConfig(BaseModel):
    alias: str
    project_id: str
    display_name: str | None = None


def get_config_path() -> Path:
    """Return the config path from OVERLEAF_MCP_CONFIG env var, or the default location."""
    override = os.environ.get("OVERLEAF_MCP_CONFIG")
    return Path(override) if override else DEFAULT_CONFIG_PATH


def load_config(path: Path) -> dict[str, ProjectConfig]:
    """Load project configs keyed by alias from a TOML file.

    Expected shape:

        [projects.<alias>]
        project_id = "..."
        display_name = "..."  # optional
    """
    if not path.exists():
        raise FileNotFoundError(f"config not found at {path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    return {
        alias: ProjectConfig(alias=alias, **fields)
        for alias, fields in data.get("projects", {}).items()
    }


def save_config(path: Path, configs: dict[str, ProjectConfig]) -> None:
    """Write project configs to a TOML file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for alias, cfg in configs.items():
        lines.append(f"[projects.{alias}]")
        lines.append(f'project_id = "{cfg.project_id}"')
        if cfg.display_name:
            lines.append(f'display_name = "{cfg.display_name}"')
        lines.append("")
    path.write_text("\n".join(lines))
