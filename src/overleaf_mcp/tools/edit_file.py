from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.paths import validate_path
from overleaf_mcp.core.project import (
    get_git_author,
    get_git_client,
    resolve_default_alias,
)


class EditFileInput(BaseModel):
    file_path: str = Field(description="Path to the file, relative to the project root.")
    content: str = Field(description="New full contents for the file.")
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="edit_file",
    description=(
        "Overwrite a file in the project: pulls from Overleaf, writes the new "
        "contents, commits with the system git author, and pushes back."
    ),
    inputSchema=EditFileInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = EditFileInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")

    author = get_git_author()
    gc = get_git_client(alias)

    gc.pull()
    validated = validate_path(gc.repo_path, args.file_path)
    gc.write_file(validated, args.content)

    if not gc.working_tree_dirty():
        return [TextContent(type="text", text=f"No changes to {args.file_path}.")]

    gc.commit(message=f"claude: edit {args.file_path}", author=author)
    gc.push()

    return [
        TextContent(
            type="text",
            text=f"Edited and pushed {args.file_path} on {alias}.",
        )
    ]
