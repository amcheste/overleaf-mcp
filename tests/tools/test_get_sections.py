import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.errors import PathEscapeError
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import get_sections


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(get_sections, "load_config", lambda _: configs)
    monkeypatch.setattr(get_sections, "get_config_path", lambda: None)
    monkeypatch.setattr(get_sections, "get_git_client", lambda _: gc)


def _fake_gc(tmp_path: Path) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    return gc


def test_lists_sections_with_levels_and_line_ranges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    (tmp_path / "main.tex").touch()
    gc.read_file.return_value = (
        "\\section{Intro}\nbody\n"
        "\\subsection{Motivation}\nm\n"
        "\\section{Method}\nm\n"
    )
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(get_sections.handle({"file_path": "main.tex"}))
    text = result[0].text
    # Each section appears with its title; subsection is indented one step.
    assert "Intro" in text
    assert "Motivation" in text
    assert "Method" in text
    # Subsection should be indented (## prefix at level 2)
    assert "## Motivation" in text
    assert "# Intro" in text
    assert "# Method" in text


def test_no_sections_emits_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    (tmp_path / "plain.tex").touch()
    gc.read_file.return_value = "just text, no sections\n"
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(get_sections.handle({"file_path": "plain.tex"}))
    assert "(no sections found in plain.tex)" in result[0].text


def test_path_escape_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(PathEscapeError):
        asyncio.run(get_sections.handle({"file_path": "../etc/passwd"}))
    gc.read_file.assert_not_called()


def test_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path)
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(get_sections.handle({"file_path": "main.tex", "project": "nope"}))
