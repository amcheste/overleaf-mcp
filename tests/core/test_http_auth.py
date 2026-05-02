import pytest

from overleaf_mcp.core.auth import (
    AUTH_TOKEN_ENV,
    check_bearer_token,
    resolve_auth_token,
)


def test_resolve_auth_token_returns_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AUTH_TOKEN_ENV, "s3cret")
    assert resolve_auth_token() == "s3cret"


def test_resolve_auth_token_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AUTH_TOKEN_ENV, "  padded  ")
    assert resolve_auth_token() == "padded"


def test_resolve_auth_token_unset_raises_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(AUTH_TOKEN_ENV, raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        resolve_auth_token()
    msg = str(exc_info.value)
    # Error must contain the env var name AND a concrete how-to-fix command
    assert AUTH_TOKEN_ENV in msg
    assert "openssl rand" in msg
    assert "Authorization: Bearer" in msg


def test_resolve_auth_token_empty_string_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(AUTH_TOKEN_ENV, "   ")
    with pytest.raises(RuntimeError, match=AUTH_TOKEN_ENV):
        resolve_auth_token()


def test_check_bearer_accepts_correct_token() -> None:
    assert check_bearer_token("Bearer s3cret", "s3cret") is True


def test_check_bearer_rejects_wrong_token() -> None:
    assert check_bearer_token("Bearer wrong", "s3cret") is False


def test_check_bearer_rejects_missing_header() -> None:
    assert check_bearer_token(None, "s3cret") is False
    assert check_bearer_token("", "s3cret") is False


def test_check_bearer_rejects_wrong_scheme() -> None:
    assert check_bearer_token("Basic s3cret", "s3cret") is False
    assert check_bearer_token("s3cret", "s3cret") is False  # missing scheme


def test_check_bearer_uses_constant_time_compare() -> None:
    """Token check must NOT short-circuit on byte-by-byte mismatch.

    Sanity check: the function uses hmac.compare_digest under the hood.
    We can't directly observe timing here, but we can at least verify the
    function exists and returns False for partial matches that would
    otherwise short-circuit a naive '==' comparison."""
    expected = "abcdefghijklmnop"
    assert check_bearer_token(f"Bearer {expected[:1]}", expected) is False
    assert check_bearer_token(f"Bearer {expected[:-1]}", expected) is False
    assert check_bearer_token(f"Bearer {expected}x", expected) is False
