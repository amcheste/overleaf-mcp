from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.project import get_git_client, resolve_default_alias


class ListFilesInput(BaseModel):
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )
    extension: str | None = Field(
        default=None,
        description="Optional file extension filter (e.g., 'tex' or '.tex').",
    )


TOOL_DEFINITION = Tool(
    name="list_files",
    description="List files tracked in the project's local git clone.",
    inputSchema=ListFilesInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = ListFilesInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")
    gc = get_git_client(alias)
    files = gc.list_files(extension=args.extension)
    if not files:
        return [TextContent(type="text", text="(no tracked files)")]
    rels = sorted(str(p.relative_to(gc.repo_path)) for p in files)
    return [TextContent(type="text", text="\n".join(rels))]
