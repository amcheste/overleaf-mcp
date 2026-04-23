import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def empty_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text("# empty\n")
    return cfg


async def test_server_lists_tools_and_responds_to_call(empty_config: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "overleaf_mcp"],
        env={**os.environ, "OVERLEAF_MCP_CONFIG": str(empty_config)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_names = {t.name for t in tools_result.tools}
            assert tool_names >= {
                "list_projects",
                "list_files",
                "read_file",
                "edit_file",
                "sync",
            }

            call_result = await session.call_tool("list_projects", {})
            texts = [c.text for c in call_result.content if hasattr(c, "text")]
            assert any("No projects configured" in t for t in texts)
