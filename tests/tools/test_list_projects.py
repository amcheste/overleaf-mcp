import asyncio

import pytest

from overleaf_mcp.core.config import ProjectConfig
from overleaf_mcp.tools import list_projects


def _patch_load(monkeypatch: pytest.MonkeyPatch, configs: dict[str, ProjectConfig]) -> None:
    monkeypatch.setattr(list_projects, "load_config", lambda _p: configs)
    monkeypatch.setattr(list_projects, "get_config_path", lambda: None)


def test_no_projects_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_load(monkeypatch, {})
    result = asyncio.run(list_projects.handle({}))
    assert "No projects configured" in result[0].text


def test_single_project_with_display_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_load(
        monkeypatch,
        {"hicss": ProjectConfig(alias="hicss", project_id="abc", display_name="HICSS 2027")},
    )
    result = asyncio.run(list_projects.handle({}))
    assert result[0].text == "hicss: HICSS 2027"


def test_multiple_projects_mixed_display_names(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_load(
        monkeypatch,
        {
            "hicss": ProjectConfig(alias="hicss", project_id="abc", display_name="HICSS"),
            "mba": ProjectConfig(alias="mba", project_id="def"),
        },
    )
    result = asyncio.run(list_projects.handle({}))
    assert result[0].text == "hicss: HICSS\nmba"


def test_tool_definition_has_name_and_schema() -> None:
    assert list_projects.TOOL_DEFINITION.name == "list_projects"
    assert list_projects.TOOL_DEFINITION.inputSchema is not None
