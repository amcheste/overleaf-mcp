import asyncio
import logging
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from overleaf_mcp.tools import (
    create_file,
    delete_file,
    edit_file,
    get_section_content,
    get_sections,
    list_files,
    list_projects,
    project_status,
    read_file,
    sync,
)


_TOOLS = [
    (list_projects.TOOL_DEFINITION, list_projects.handle),
    (list_files.TOOL_DEFINITION, list_files.handle),
    (read_file.TOOL_DEFINITION, read_file.handle),
    (get_sections.TOOL_DEFINITION, get_sections.handle),
    (get_section_content.TOOL_DEFINITION, get_section_content.handle),
    (edit_file.TOOL_DEFINITION, edit_file.handle),
    (create_file.TOOL_DEFINITION, create_file.handle),
    (delete_file.TOOL_DEFINITION, delete_file.handle),
    (sync.TOOL_DEFINITION, sync.handle),
    (project_status.TOOL_DEFINITION, project_status.handle),
]


def _configure_logging() -> None:
    level = logging.DEBUG if os.environ.get("OVERLEAF_MCP_DEBUG") else logging.WARNING
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


def build_server() -> Server:
    server: Server = Server("overleaf-mcp")
    handlers = {tool.name: handler for tool, handler in _TOOLS}

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return [tool for tool, _ in _TOOLS]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name not in handlers:
            raise ValueError(f"unknown tool: {name}")
        return await handlers[name](arguments)

    return server


async def _run() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    _configure_logging()
    asyncio.run(_run())
