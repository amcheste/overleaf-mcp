import os

import keyring
import pytest

from overleaf_mcp.core.credentials import ACCOUNT_LEVEL_KEY, SERVICE, resolve_token
from overleaf_mcp.core.errors import TokenNotFoundError


@pytest.fixture(autouse=True)
def _clear_overleaf_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OVERLEAF_TOKEN", raising=False)
    for var in list(os.environ):
        if var.startswith("OVERLEAF_TOKEN_"):
            monkeypatch.delenv(var, raising=False)


def test_project_scoped_keyring_wins(fake_keyring: None, monkeypatch: pytest.MonkeyPatch) -> None:
    keyring.set_password(SERVICE, "hicss", "project-token")
    keyring.set_password(SERVICE, ACCOUNT_LEVEL_KEY, "account-token")
    monkeypatch.setenv("OVERLEAF_TOKEN_HICSS", "env-project")
    monkeypatch.setenv("OVERLEAF_TOKEN", "env-account")
    assert resolve_token("hicss") == "project-token"


def test_account_keyring_used_when_project_missing(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    keyring.set_password(SERVICE, ACCOUNT_LEVEL_KEY, "account-token")
    monkeypatch.setenv("OVERLEAF_TOKEN_HICSS", "env-project")
    assert resolve_token("hicss") == "account-token"


def test_project_env_var_used_when_keyring_empty(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OVERLEAF_TOKEN_HICSS", "env-project")
    monkeypatch.setenv("OVERLEAF_TOKEN", "env-account")
    assert resolve_token("hicss") == "env-project"


def test_global_env_var_used_as_last_resort(
    fake_keyring: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OVERLEAF_TOKEN", "env-account")
    assert resolve_token("hicss") == "env-account"


def test_alias_normalized_for_env(fake_keyring: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OVERLEAF_TOKEN_HICSS2027", "token")
    assert resolve_token("hicss2027") == "token"


def test_raises_when_nothing_found(fake_keyring: None) -> None:
    with pytest.raises(TokenNotFoundError, match="hicss"):
        resolve_token("hicss")
