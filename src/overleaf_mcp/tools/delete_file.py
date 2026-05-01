from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.paths import validate_path
from overleaf_mcp.core.project import (
    get_git_author,
    get_git_client,
    resolve_default_alias,
)


class DeleteFileInput(BaseModel):
    file_path: str = Field(
        description="Path of the file to delete, relative to the project root."
    )
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="delete_file",
    description=(
        "Delete a file from the project. Errors if the file doesn't exist. "
        "Pulls latest before deleting, commits as the system git author, "
        "and pushes back to Overleaf."
    ),
    inputSchema=DeleteFileInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = DeleteFileInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")

    author = get_git_author()
    gc = get_git_client(alias)

    gc.pull()
    validated = validate_path(gc.repo_path, args.file_path)
    if not validated.exists():
        raise FileNotFoundError(f"{args.file_path} does not exist on {alias}")

    gc.delete_file(validated)
    gc.commit(message=f"claude: delete {args.file_path}", author=author)
    gc.push()

    return [
        TextContent(
            type="text",
            text=f"Deleted {args.file_path} on {alias}.",
        )
    ]
