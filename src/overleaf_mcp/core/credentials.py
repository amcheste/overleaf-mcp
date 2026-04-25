import os

import keyring

from overleaf_mcp.core.errors import TokenNotFoundError


SERVICE = "overleaf-mcp"
ACCOUNT_LEVEL_KEY = "__account__"


def _key_for(alias: str | None) -> str:
    return alias if alias else ACCOUNT_LEVEL_KEY


def store_token(alias: str | None, token: str) -> None:
    """Store a token in the keyring. alias=None stores the account-level fallback."""
    keyring.set_password(SERVICE, _key_for(alias), token)


def delete_token(alias: str | None) -> bool:
    """Remove a token. Returns False if none was stored; True if one was removed."""
    try:
        keyring.delete_password(SERVICE, _key_for(alias))
        return True
    except keyring.errors.PasswordDeleteError:
        return False


def has_token(alias: str | None) -> bool:
    return keyring.get_password(SERVICE, _key_for(alias)) is not None


def resolve_token(alias: str) -> str:
    """Find an Overleaf token for the given project alias.

    Resolution order:
      1. Keyring entry for this alias
      2. Keyring account-level fallback
      3. OVERLEAF_TOKEN_<ALIAS> environment variable (alias upper-cased)
      4. OVERLEAF_TOKEN environment variable

    Raises TokenNotFoundError if no source yields a token.
    """
    token = keyring.get_password(SERVICE, alias)
    if token:
        return token

    token = keyring.get_password(SERVICE, ACCOUNT_LEVEL_KEY)
    if token:
        return token

    token = os.environ.get(f"OVERLEAF_TOKEN_{alias.upper()}")
    if token:
        return token

    token = os.environ.get("OVERLEAF_TOKEN")
    if token:
        return token

    raise TokenNotFoundError(
        f"no Overleaf token found for '{alias}'. Register one with "
        f"'overleaf-mcp auth add --project {alias}' or set OVERLEAF_TOKEN."
    )
