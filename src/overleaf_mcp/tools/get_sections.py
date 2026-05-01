from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.latex import RegexSectionParser
from overleaf_mcp.core.paths import validate_path
from overleaf_mcp.core.project import get_git_client, resolve_default_alias


class GetSectionsInput(BaseModel):
    file_path: str = Field(
        description="Path to the .tex file relative to the project root."
    )
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="get_sections",
    description=(
        "List all LaTeX sections in a file with their nesting level and "
        "line ranges. Use this before get_section_content to discover what's "
        "available."
    ),
    inputSchema=GetSectionsInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = GetSectionsInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")
    gc = get_git_client(alias)
    validated = validate_path(gc.repo_path, args.file_path)
    sections = RegexSectionParser().parse(gc.read_file(validated))
    if not sections:
        return [
            TextContent(
                type="text",
                text=f"(no sections found in {args.file_path})",
            )
        ]
    lines = [
        f"L{s.start_line:>4}-{s.end_line:<4}  {'  ' * (s.level - 1)}{'#' * s.level} {s.title}"
        for s in sections
    ]
    return [TextContent(type="text", text="\n".join(lines))]
