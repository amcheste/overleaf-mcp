import keyring

from overleaf_mcp.core.credentials import (
    ACCOUNT_LEVEL_KEY,
    SERVICE,
    delete_token,
    has_token,
    store_token,
)


def test_store_and_has_token_for_alias(fake_keyring: None) -> None:
    assert has_token("hicss") is False
    store_token("hicss", "secret")
    assert has_token("hicss") is True
    assert keyring.get_password(SERVICE, "hicss") == "secret"


def test_store_account_level_when_alias_none(fake_keyring: None) -> None:
    store_token(None, "account-secret")
    assert keyring.get_password(SERVICE, ACCOUNT_LEVEL_KEY) == "account-secret"
    assert has_token(None) is True


def test_delete_token_returns_true_when_present(fake_keyring: None) -> None:
    store_token("hicss", "secret")
    assert delete_token("hicss") is True
    assert has_token("hicss") is False


def test_delete_token_returns_false_when_absent(fake_keyring: None) -> None:
    assert delete_token("never-stored") is False
