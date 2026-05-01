import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.core.git_client import GitClient
from overleaf_mcp.tools import get_section_content


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    configs: dict[str, ProjectConfig],
    gc: MagicMock,
) -> None:
    monkeypatch.setattr(get_section_content, "load_config", lambda _: configs)
    monkeypatch.setattr(get_section_content, "get_config_path", lambda: None)
    monkeypatch.setattr(get_section_content, "get_git_client", lambda _: gc)


def _fake_gc(tmp_path: Path, content: str) -> MagicMock:
    gc = MagicMock(spec=GitClient)
    gc.repo_path = tmp_path
    (tmp_path / "main.tex").touch()
    gc.read_file.return_value = content
    return gc


def test_returns_section_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(
        tmp_path,
        "\\section{Intro}\nIntro body line 1\nIntro body line 2\n"
        "\\section{Method}\nMethod body\n",
    )
    _patch(monkeypatch, configs, gc)

    result = asyncio.run(
        get_section_content.handle({"file_path": "main.tex", "title": "Intro"})
    )
    assert "Intro body line 1" in result[0].text
    assert "Intro body line 2" in result[0].text
    assert "Method" not in result[0].text  # stops at next header


def test_missing_title_lists_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(
        tmp_path,
        "\\section{Intro}\nx\n\\section{Method}\ny\n",
    )
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError) as exc_info:
        asyncio.run(
            get_section_content.handle(
                {"file_path": "main.tex", "title": "Conclusion"}
            )
        )
    msg = str(exc_info.value)
    # Error must contain the requested title AND the list of valid options.
    assert "Conclusion" in msg
    assert "Intro" in msg
    assert "Method" in msg


def test_unknown_alias_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(tmp_path, "")
    _patch(monkeypatch, configs, gc)

    with pytest.raises(KeyError, match="unknown project alias"):
        asyncio.run(
            get_section_content.handle(
                {"file_path": "main.tex", "title": "X", "project": "nope"}
            )
        )
    gc.read_file.assert_not_called()


def test_ambiguous_title_errors_with_locations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    configs = {"hicss": ProjectConfig(alias="hicss", project_id="abc")}
    gc = _fake_gc(
        tmp_path,
        "\\section{Notes}\nfirst\n\\section{Other}\nx\n\\section{Notes}\nsecond\n",
    )
    _patch(monkeypatch, configs, gc)

    with pytest.raises(ValueError, match="2 sections named 'Notes'"):
        asyncio.run(
            get_section_content.handle({"file_path": "main.tex", "title": "Notes"})
        )
