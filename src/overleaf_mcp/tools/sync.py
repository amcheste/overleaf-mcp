from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.project import get_git_client, resolve_default_alias


class SyncInput(BaseModel):
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="sync",
    description="Pull the latest changes from Overleaf into the local clone.",
    inputSchema=SyncInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = SyncInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")
    gc = get_git_client(alias)

    before = gc.current_head()
    gc.pull()
    after = gc.current_head()

    if before == after:
        return [TextContent(type="text", text=f"Already up to date on {alias}.")]
    return [TextContent(type="text", text=f"Synced {alias}: pulled new commits.")]
