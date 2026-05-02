import hmac
import os


AUTH_TOKEN_ENV = "OVERLEAF_MCP_AUTH_TOKEN"


def resolve_auth_token() -> str:
    """Return the bearer token the HTTP transport will require, or raise.

    The HTTP transport refuses to start without a token because it would
    expose every Overleaf token in the OS keychain to anyone who can reach
    the bound port. There is no "open mode" by design.
    """
    token = os.environ.get(AUTH_TOKEN_ENV, "").strip()
    if not token:
        raise RuntimeError(
            f"{AUTH_TOKEN_ENV} is not set. The HTTP transport requires a "
            f"bearer token. Set the env var to a strong secret before "
            f"running 'overleaf-mcp serve-http' — e.g.\n"
            f"  export {AUTH_TOKEN_ENV}=\"$(openssl rand -hex 32)\"\n"
            f"Then send the same value as 'Authorization: Bearer <token>' "
            f"on every request."
        )
    return token


def check_bearer_token(header_value: str | None, expected: str) -> bool:
    """Constant-time check of an Authorization header against expected token.

    Returns True iff the header is exactly 'Bearer <expected>'. Uses
    hmac.compare_digest so timing on a partial-match attempt doesn't leak
    the token byte-by-byte.
    """
    if not header_value:
        return False
    if not header_value.startswith("Bearer "):
        return False
    presented = header_value[len("Bearer ") :]
    return hmac.compare_digest(presented.encode(), expected.encode())
