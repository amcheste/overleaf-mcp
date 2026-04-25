from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.paths import validate_path
from overleaf_mcp.core.project import get_git_client, resolve_default_alias


class ReadFileInput(BaseModel):
    file_path: str = Field(description="Path to the file, relative to the project root.")
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="read_file",
    description="Read a file from the project's local git clone.",
    inputSchema=ReadFileInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = ReadFileInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")
    gc = get_git_client(alias)
    validated = validate_path(gc.repo_path, args.file_path)
    return [TextContent(type="text", text=gc.read_file(validated))]
