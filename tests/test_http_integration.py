"""End-to-end test of the Streamable HTTP transport.

Spins up the real Starlette app via httpx.ASGITransport (no socket bind,
no port collision risk in CI) and exercises:

  - 401 with no Authorization header
  - 401 with wrong bearer token
  - 200 on /healthz with no auth (deliberately exempt for monitoring)
  - Full MCP handshake + tool list + tool call with valid bearer token

The MCP wire flow uses the SDK's ``streamablehttp_client`` so we exercise
the same code path Claude Desktop / claude.ai web would use. The
ASGITransport adapter is plugged into httpx so all traffic stays in
process — no flaky port-binding waits.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


_AUTH_TOKEN = "test-token-deadbeef"


@pytest.fixture
def empty_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text("# empty\n")
    return cfg


@pytest.fixture
async def http_client(
    monkeypatch: pytest.MonkeyPatch, empty_config: Path
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an httpx.AsyncClient bound to the real ASGI app, no socket."""
    monkeypatch.setenv("OVERLEAF_MCP_AUTH_TOKEN", _AUTH_TOKEN)
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(empty_config))

    from overleaf_mcp.transports.streamable_http import build_app

    app = build_app(_AUTH_TOKEN)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        # Run the lifespan so the StreamableHTTPSessionManager starts.
        async with _lifespan(app, transport):
            yield client


@asynccontextmanager
async def _lifespan(app, transport: httpx.ASGITransport):
    """Drive the Starlette lifespan protocol manually so tests can use
    httpx.ASGITransport without the lifespan being skipped (httpx's
    ASGITransport doesn't call lifespan by default)."""
    scope = {"type": "lifespan"}
    receive_queue: list[dict] = [{"type": "lifespan.startup"}]
    sent: list[dict] = []

    async def receive():
        return receive_queue.pop(0) if receive_queue else {"type": "lifespan.shutdown"}

    async def send(message):
        sent.append(message)

    import asyncio
    task = asyncio.create_task(app(scope, receive, send))
    # Wait for startup.complete
    while not any(m["type"] == "lifespan.startup.complete" for m in sent):
        await asyncio.sleep(0.01)
    try:
        yield
    finally:
        receive_queue.append({"type": "lifespan.shutdown"})
        await task


async def test_healthz_exempt_from_auth(http_client: httpx.AsyncClient) -> None:
    """Monitoring should hit /healthz without a credential."""
    r = await http_client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_mcp_endpoint_requires_auth(http_client: httpx.AsyncClient) -> None:
    """No Authorization header → 401, with WWW-Authenticate hint."""
    r = await http_client.post("/mcp")
    assert r.status_code == 401
    assert "Bearer" in r.headers.get("WWW-Authenticate", "")
    assert "unauthorized" in r.json().get("error", "").lower()


async def test_mcp_endpoint_rejects_wrong_token(
    http_client: httpx.AsyncClient,
) -> None:
    r = await http_client.post(
        "/mcp", headers={"Authorization": "Bearer wrong-token"}
    )
    assert r.status_code == 401


async def test_mcp_endpoint_rejects_wrong_scheme(
    http_client: httpx.AsyncClient,
) -> None:
    r = await http_client.post(
        "/mcp", headers={"Authorization": f"Basic {_AUTH_TOKEN}"}
    )
    assert r.status_code == 401


async def test_full_mcp_round_trip_with_valid_bearer(
    monkeypatch: pytest.MonkeyPatch, empty_config: Path, unused_tcp_port: int
) -> None:
    """Real socket spin-up — bind on an OS-assigned free port, run uvicorn
    in a thread, drive the MCP protocol with the SDK's HTTP client.

    Slower than the ASGI-transport tests but proves the stack works
    end-to-end: bearer auth, MCP handshake, list_tools, call_tool, all
    over real HTTP."""
    import asyncio
    import threading
    import time

    import uvicorn

    monkeypatch.setenv("OVERLEAF_MCP_AUTH_TOKEN", _AUTH_TOKEN)
    monkeypatch.setenv("OVERLEAF_MCP_CONFIG", str(empty_config))

    from overleaf_mcp.transports.streamable_http import build_app

    app = build_app(_AUTH_TOKEN)
    config = uvicorn.Config(
        app, host="127.0.0.1", port=unused_tcp_port, log_level="warning"
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        # Wait for uvicorn to come up
        deadline = time.time() + 5.0
        while time.time() < deadline and not server.started:
            await asyncio.sleep(0.05)
        assert server.started, "uvicorn failed to start within 5s"

        # Trailing slash matters: Starlette's Mount("/mcp") expects the
        # full mounted path, /mcp/. The MCP client doesn't follow the
        # 307 redirect that /mcp (no slash) would issue.
        url = f"http://127.0.0.1:{unused_tcp_port}/mcp/"

        # The MCP HTTP client's auth model: pass a pre-configured
        # httpx.AsyncClient with the bearer header baked in. The client
        # owns transport-level concerns, MCP just speaks JSON-RPC over it.
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {_AUTH_TOKEN}"}
        ) as auth_client:
            async with streamable_http_client(url, http_client=auth_client) as (
                read,
                write,
                _get_session_id,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = {t.name for t in tools.tools}
                    assert tool_names >= {
                        "list_projects",
                        "list_files",
                        "read_file",
                        "edit_file",
                        "sync",
                        "get_sections",
                        "get_section_content",
                        "create_file",
                        "delete_file",
                        "project_status",
                    }, f"missing tools: {tool_names}"

                    result = await session.call_tool("list_projects", {})
                    texts = [
                        c.text for c in result.content if hasattr(c, "text")
                    ]
                    assert any("No projects configured" in t for t in texts)
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


@pytest.fixture
def unused_tcp_port() -> int:
    """Allocate an ephemeral port the OS has confirmed is free."""
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
