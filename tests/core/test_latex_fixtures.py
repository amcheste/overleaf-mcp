"""Regression tests against real-world-shaped LaTeX fixtures.

These fixtures live in tests/fixtures/latex/ and are checked in. They
exercise the parser against shapes we'd see in actual academic projects:
nested document structure, \\input{}/\\include{} directives, inline
comments on section lines, and known-limitation cases like nested braces
in titles.

The point isn't to assert pretty results — some inputs hit known parser
limits. The point is to *lock in* what we currently do, so a future
swap to pylatexenc (or any other parser) trips a clear regression test
instead of silently changing observable behavior.
"""

from pathlib import Path

from overleaf_mcp.core.latex import RegexSectionParser


FIXTURES = Path(__file__).parent.parent / "fixtures" / "latex"


def _parse(name: str) -> list:
    return RegexSectionParser().parse((FIXTURES / name).read_text())


def test_realistic_paper_full_structure() -> None:
    sections = _parse("realistic_paper.tex")
    titles = [(s.title, s.level) for s in sections]
    assert titles == [
        ("Introduction", 1),
        ("Motivation", 2),
        ("Contributions", 2),
        ("Related Work", 1),
        ("Foundational papers", 2),
        ("Seminal work", 3),
        ("Recent surveys", 3),
        ("Method", 1),
        ("Acknowledgements", 1),  # starred section is still captured
    ]


def test_realistic_paper_section_slicing_stops_at_any_next_header() -> None:
    """Each section's content runs up to (not including) the next header at
    *any* level — including its own subsections. So the Introduction's
    content is just the prose between \\section{Introduction} and the
    first subsection that follows. Documenting this so a future change to
    nested-content semantics breaks this test loudly."""
    sections = _parse("realistic_paper.tex")
    intro = next(s for s in sections if s.title == "Introduction")
    assert "It motivates the work" in intro.content
    assert "Motivation" not in intro.content
    assert "Related Work" not in intro.content


def test_input_and_include_directives_are_not_followed() -> None:
    sections = _parse("inputs_and_includes.tex")
    # \input{sections/methods} and \include{sections/results} appear as
    # plain text in the section body — the parser deliberately doesn't
    # follow them (single-file scope is documented). Two real sections
    # only.
    titles = [s.title for s in sections]
    assert titles == ["Top Level", "Discussion"]


def test_inline_comments_after_section_command_do_not_break_parsing() -> None:
    sections = _parse("inline_comments.tex")
    titles = [s.title for s in sections]
    # Both real sections are picked up — the trailing % todo / FIXME
    # comments don't interfere because the regex anchors on the start of
    # the line.
    assert titles == ["Real Section", "Another Section"]


def test_fully_commented_section_lines_are_ignored() -> None:
    sections = _parse("inline_comments.tex")
    # The file contains a "% \\section{...}" line. It must NOT appear.
    titles = [s.title for s in sections]
    assert "This is a commented-out section directive" not in titles


def test_nested_braces_in_title_is_truncated_not_crashed() -> None:
    """Documents the known limitation: titles with nested {} groups
    get truncated at the first close brace. Asserting this so any future
    fix (likely a pylatexenc swap) breaks this test loudly and we update
    it as part of that change."""
    sections = _parse("nested_braces.tex")
    assert len(sections) == 2
    truncated, plain = sections
    # First section's title is captured up to the first '}' (i.e. before
    # "Nested}"), so we get "A Title With {Nested" — known regex limit.
    assert truncated.title == "A Title With {Nested"
    assert plain.title == "Plain Title"
