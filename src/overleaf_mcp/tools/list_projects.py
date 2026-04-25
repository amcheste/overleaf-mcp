from mcp.types import TextContent, Tool
from pydantic import BaseModel

from overleaf_mcp.core.config import get_config_path, load_config


class ListProjectsInput(BaseModel):
    pass


TOOL_DEFINITION = Tool(
    name="list_projects",
    description="List the Overleaf projects configured for this server.",
    inputSchema=ListProjectsInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    configs = load_config(get_config_path())
    if not configs:
        return [
            TextContent(
                type="text",
                text="No projects configured. Run 'overleaf-mcp init' to add one.",
            )
        ]
    lines = [
        f"{alias}: {cfg.display_name}" if cfg.display_name else alias
        for alias, cfg in configs.items()
    ]
    return [TextContent(type="text", text="\n".join(lines))]
