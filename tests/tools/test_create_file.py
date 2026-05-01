import asyncio
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.errors import PathEscapeError
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import create_file


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
    author: str = "Tester <tester@example.com>",
) -> None:
    monkeypatch.setattr(create_file, "load_config", lambda _: configs)
    monkeypatch.setattr(create_file, "get_config_path", lambda: None)
    monkeypatch.setattr(create_file, "get_git_client", lambda _: gc)
    monkeypatch.setattr(create_file, "get_git_author", lambda: author)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_create_file_full_flow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(
        create_file.handle({"file_path": "sections/new.tex", "content": "hello\n"})
    )

    expected_path = (tmp_path / "sections" / "new.tex").resolve()
    assert gc.mock_calls == [
        call.pull(),
        call.write_file(expected_path, "hello\n"),
        call.commit(
            message="claude: create sections/new.tex",
            author="Tester <tester@example.com>",
        ),
        call.push(),
    ]
    assert "Created sections/new.tex on hicss" in result[0].text


def test_create_file_rejects_existing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    (tmp_path / "exists.tex").touch()
    _patch(monkeypatch, configs, gc)

    with pytest.raises(FileExistsError, match="use edit_file to overwrite"):
        asyncio.run(
            create_file.handle({"file_path": "exists.tex", "content": "x"})
        )
    gc.write_file.assert_not_called()
    gc.commit.assert_not_called()


def test_create_file_path_escape_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(PathEscapeError):
        asyncio.run(
            create_file.handle({"file_path": "../outside", "content": "x"})
        )
    gc.write_file.assert_not_called()


def test_create_file_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(
            create_file.handle(
                {"file_path": "x.tex", "content": "y", "project": "missing"}
            )
        )
    gc.pull.assert_not_called()


def test_create_file_git_author_failure_aborts_before_pull(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    monkeypatch.setattr(create_file, "load_config", lambda _: configs)
    monkeypatch.setattr(create_file, "get_config_path", lambda: None)
    monkeypatch.setattr(create_file, "get_git_client", lambda _: gc)

    def _boom() -> str:
        raise RuntimeError("git config user.name is not set")

    monkeypatch.setattr(create_file, "get_git_author", _boom)

    with pytest.raises(RuntimeError, match="not set"):
        asyncio.run(
            create_file.handle({"file_path": "x.tex", "content": "y"})
        )
    gc.pull.assert_not_called()
