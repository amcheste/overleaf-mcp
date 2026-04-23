import pytest

from overleaf_mcp.core.latex import RegexSectionParser, SectionParser


def test_parses_single_section() -> None:
    content = "\\section{Intro}\nHello world.\n"
    sections = RegexSectionParser().parse(content)
    assert len(sections) == 1
    s = sections[0]
    assert s.title == "Intro"
    assert s.level == 1
    assert s.start_line == 1
    assert s.end_line == 2
    assert s.content == "\\section{Intro}\nHello world."


def test_parses_multiple_sections() -> None:
    content = "\\section{A}\nbody a\n\\section{B}\nbody b\n"
    sections = RegexSectionParser().parse(content)
    assert [s.title for s in sections] == ["A", "B"]
    assert sections[0].end_line == 2
    assert sections[1].start_line == 3
    assert sections[1].end_line == 4


def test_parses_subsections_with_correct_levels() -> None:
    content = "\\section{A}\n\\subsection{B}\n\\subsubsection{C}\n"
    sections = RegexSectionParser().parse(content)
    assert [s.level for s in sections] == [1, 2, 3]


def test_starred_variants_parsed() -> None:
    content = "\\section*{Preface}\n\\subsection*{Sub}\n"
    sections = RegexSectionParser().parse(content)
    assert [s.title for s in sections] == ["Preface", "Sub"]
    assert [s.level for s in sections] == [1, 2]


def test_commented_lines_ignored() -> None:
    content = "% \\section{Fake}\n\\section{Real}\nbody\n"
    sections = RegexSectionParser().parse(content)
    assert len(sections) == 1
    assert sections[0].title == "Real"
    assert sections[0].start_line == 2


def test_indented_commented_lines_ignored() -> None:
    content = "  % \\section{Fake}\n\\section{Real}\n"
    sections = RegexSectionParser().parse(content)
    assert [s.title for s in sections] == ["Real"]


def test_leading_whitespace_allowed() -> None:
    content = "   \\section{Indented}\n"
    sections = RegexSectionParser().parse(content)
    assert sections[0].title == "Indented"


def test_section_not_at_start_of_line_ignored() -> None:
    content = "text before \\section{NotASection}\n"
    sections = RegexSectionParser().parse(content)
    assert sections == []


def test_empty_content_returns_empty_list() -> None:
    assert RegexSectionParser().parse("") == []


def test_content_without_sections_returns_empty_list() -> None:
    assert RegexSectionParser().parse("just some text\nno sections\n") == []


def test_section_parser_is_abstract() -> None:
    with pytest.raises(TypeError):
        SectionParser()  # type: ignore[abstract]
