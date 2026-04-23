import re
from abc import ABC, abstractmethod

from pydantic import BaseModel


class Section(BaseModel):
    title: str
    level: int
    start_line: int
    end_line: int
    content: str


class SectionParser(ABC):
    @abstractmethod
    def parse(self, content: str) -> list[Section]:
        ...


class RegexSectionParser(SectionParser):
    """Regex-based LaTeX section parser.

    Matches \\section, \\subsection, \\subsubsection (and starred variants)
    when they appear at the start of a line, ignoring any line whose first
    non-whitespace character is ``%``.

    Known limitations:
      - Titles containing nested ``{...}`` groups are not parsed correctly.
      - ``\\input{}`` / ``\\include{}`` are not followed across files.
      - Does not expand user-defined section macros.
    """

    _LEVEL = {"section": 1, "subsection": 2, "subsubsection": 3}
    _SECTION_LINE_RE = re.compile(
        r"^\s*\\(section|subsection|subsubsection)\*?\{([^}]*)\}"
    )
    _COMMENT_LINE_RE = re.compile(r"^\s*%")

    def parse(self, content: str) -> list[Section]:
        lines = content.splitlines()
        headers: list[tuple[int, int, str]] = []

        for i, line in enumerate(lines):
            if self._COMMENT_LINE_RE.match(line):
                continue
            m = self._SECTION_LINE_RE.match(line)
            if m:
                kind, title = m.group(1), m.group(2)
                headers.append((i, self._LEVEL[kind], title))

        sections: list[Section] = []
        for idx, (line_idx, level, title) in enumerate(headers):
            start = line_idx + 1
            end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
            sections.append(
                Section(
                    title=title,
                    level=level,
                    start_line=start,
                    end_line=end,
                    content="\n".join(lines[line_idx:end]),
                )
            )

        return sections
