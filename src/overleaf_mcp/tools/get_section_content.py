from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.latex import RegexSectionParser
from overleaf_mcp.core.paths import validate_path
from overleaf_mcp.core.project import get_git_client, resolve_default_alias


class GetSectionContentInput(BaseModel):
    file_path: str = Field(
        description="Path to the .tex file relative to the project root."
    )
    title: str = Field(
        description="Exact title of the section to extract (case-sensitive)."
    )
    project: str | None = Field(
        default=None,
        description="Project alias. Omit when only one project is configured.",
    )


TOOL_DEFINITION = Tool(
    name="get_section_content",
    description=(
        "Return the body of a specific named section from a .tex file, "
        "from its header line through the line before the next header at "
        "any level. Errors if the title isn't found or matches more than "
        "one section."
    ),
    inputSchema=GetSectionContentInput.model_json_schema(),
)


async def handle(arguments: dict) -> list[TextContent]:
    args = GetSectionContentInput(**arguments)
    configs = load_config(get_config_path())
    alias = args.project or resolve_default_alias(configs)
    if alias not in configs:
        raise KeyError(f"unknown project alias '{alias}'")
    gc = get_git_client(alias)
    validated = validate_path(gc.repo_path, args.file_path)
    sections = RegexSectionParser().parse(gc.read_file(validated))

    matches = [s for s in sections if s.title == args.title]
    if not matches:
        available = sorted({s.title for s in sections})
        raise KeyError(
            f"section '{args.title}' not found in {args.file_path}. "
            f"Available titles: {available}"
        )
    if len(matches) > 1:
        locations = [f"L{s.start_line}-{s.end_line}" for s in matches]
        raise ValueError(
            f"{len(matches)} sections named '{args.title}' in {args.file_path} "
            f"at {locations}; use a more unique title or call get_sections first"
        )

    return [TextContent(type="text", text=matches[0].content)]
