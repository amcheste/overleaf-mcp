import contextlib
import logging
import os
import sys

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from overleaf_mcp.core.auth import check_bearer_token, resolve_auth_token
from overleaf_mcp.transports.stdio import build_server


_MCP_PATH = "/mcp"
_HEALTH_PATH = "/healthz"


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests that don't carry the right Authorization header.

    The /healthz endpoint is intentionally exempt so monitoring can hit it
    without a credential. Every other path requires 'Bearer <token>'.
    """

    def __init__(self, app, expected_token: str) -> None:
        super().__init__(app)
        self._expected_token = expected_token

    async def dispatch(self, request: Request, call_next):
        if request.url.path == _HEALTH_PATH:
            return await call_next(request)
        header = request.headers.get("Authorization")
        if not check_bearer_token(header, self._expected_token):
            return JSONResponse(
                {"error": "unauthorized: provide Authorization: Bearer <token>"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)


async def _healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _configure_logging() -> None:
    level = logging.DEBUG if os.environ.get("OVERLEAF_MCP_DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


def build_app(token: str) -> Starlette:
    """Build the Starlette ASGI app: MCP server + bearer auth + healthz.

    Exposed for testing — call this with a known token to drive the app
    via httpx.AsyncClient or the MCP SDK's HTTP client without ever
    binding a real socket.
    """
    server = build_server()
    manager = StreamableHTTPSessionManager(app=server, stateless=False)

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        async with manager.run():
            yield

    return Starlette(
        routes=[
            Mount(_MCP_PATH, app=manager.handle_request),
            Route(_HEALTH_PATH, _healthz, methods=["GET"]),
        ],
        lifespan=lifespan,
        middleware=[Middleware(BearerAuthMiddleware, expected_token=token)],
    )


def main(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the HTTP transport on host:port. Requires OVERLEAF_MCP_AUTH_TOKEN."""
    _configure_logging()
    token = resolve_auth_token()  # raises with actionable message if unset
    app = build_app(token)
    logging.getLogger(__name__).info(
        "overleaf-mcp HTTP listening on http://%s:%d%s (auth: bearer)",
        host,
        port,
        _MCP_PATH,
    )
    uvicorn.run(app, host=host, port=port, log_config=None)
