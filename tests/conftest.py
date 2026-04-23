from collections.abc import Iterator
from pathlib import Path

import keyring
import keyrings.alt.file
import pytest


@pytest.fixture
def fake_keyring(tmp_path: Path) -> Iterator[None]:
    """Swap in a file-backed keyring in tmp_path for the duration of a test."""
    backend = keyrings.alt.file.PlaintextKeyring()
    backend.file_path = str(tmp_path / "keyring.cfg")
    previous = keyring.get_keyring()
    keyring.set_keyring(backend)
    try:
        yield
    finally:
        keyring.set_keyring(previous)
