from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.project import get_git_client, resolve_default_alias


class ProjectStatusInput(BaseModel):
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="project_status",
    description=(
        "Summary of a project's local clone: tracked file count, working "
        "tree dirty status, and the last commit (short SHA, author, "
        "relative date, subject)."
    ),
    inputSchema=ProjectStatusInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = ProjectStatusInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")

    cfg = configs[alias]
    gc = get_git_client(alias)

    file_count = len(gc.list_files())
    dirty = "yes" if gc.working_tree_dirty() else "no"
    last_commit = gc.last_commit_summary()

    display = f" ({cfg.display_name})" if cfg.display_name else ""
    text = (
        f"Project: {alias}{display}\n"
        f"Files tracked: {file_count}\n"
        f"Working tree dirty: {dirty}\n"
        f"\n"
        f"Last commit:\n{last_commit}"
    )
    return [TextContent(type="text", text=text)]
