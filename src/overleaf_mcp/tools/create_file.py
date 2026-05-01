from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.paths import validate_path
from overleaf_mcp.core.project import (
    get_git_author,
    get_git_client,
    resolve_default_alias,
)


class CreateFileInput(BaseModel):
    file_path: str = Field(
        description="Path of the new file, relative to the project root."
    )
    content: str = Field(description="Initial contents for the new file.")
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="create_file",
    description=(
        "Create a new file in the project. Errors if the file already "
        "exists — use edit_file to overwrite. Pulls latest before writing, "
        "commits as the system git author, and pushes back to Overleaf."
    ),
    inputSchema=CreateFileInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = CreateFileInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")

    author = get_git_author()
    gc = get_git_client(alias)

    gc.pull()
    validated = validate_path(gc.repo_path, args.file_path)
    if validated.exists():
        raise FileExistsError(
            f"{args.file_path} already exists on {alias}; "
            f"use edit_file to overwrite"
        )

    gc.write_file(validated, args.content)
    gc.commit(message=f"claude: create {args.file_path}", author=author)
    gc.push()

    return [
        TextContent(
            type="text",
            text=f"Created {args.file_path} on {alias}.",
        )
    ]
