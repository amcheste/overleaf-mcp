from pathlib import Path

import pytest

from overleaf_mcp.core.errors import PathEscapeError
from overleaf_mcp.core.paths import validate_path


def test_valid_relative_path(tmp_path: Path) -> None:
    (tmp_path / "file.tex").touch()
    result = validate_path(tmp_path, "file.tex")
    assert result == (tmp_path / "file.tex").resolve()


def test_nested_relative_path(tmp_path: Path) -> None:
    (tmp_path / "sections").mkdir()
    (tmp_path / "sections" / "intro.tex").touch()
    result = validate_path(tmp_path, "sections/intro.tex")
    assert result == (tmp_path / "sections" / "intro.tex").resolve()


def test_absolute_path_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathEscapeError, match="absolute"):
        validate_path(tmp_path, "/etc/passwd")


def test_windows_absolute_path_rejected_on_any_os(tmp_path: Path) -> None:
    """Windows-style absolute paths must be rejected even on POSIX runners.

    Regression test for the Windows CI failure: Path.is_absolute() is
    platform-specific, so 'C:\\evil' is not absolute on POSIX and the
    early-reject didn't fire — defense-in-depth caught it later as a
    path-escape, but with the wrong error code path. The fix uses
    PurePosixPath OR PureWindowsPath to catch both formats everywhere."""
    with pytest.raises(PathEscapeError, match="absolute"):
        validate_path(tmp_path, r"C:\Windows\System32\config")
    with pytest.raises(PathEscapeError, match="absolute"):
        validate_path(tmp_path, r"\\server\share\file.tex")


def test_dotdot_stays_inside(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b.tex").touch()
    result = validate_path(tmp_path, "a/../b.tex")
    assert result == (tmp_path / "b.tex").resolve()


def test_dotdot_escape_rejected(tmp_path: Path) -> None:
    with pytest.raises(PathEscapeError, match="escapes"):
        validate_path(tmp_path, "../outside")


def test_complex_dotdot_escape_rejected(tmp_path: Path) -> None:
    (tmp_path / "a" / "b").mkdir(parents=True)
    with pytest.raises(PathEscapeError, match="escapes"):
        validate_path(tmp_path, "a/b/../../../outside")


def test_nonexistent_target_ok(tmp_path: Path) -> None:
    result = validate_path(tmp_path, "new/nested/file.tex")
    assert result == (tmp_path / "new" / "nested" / "file.tex").resolve()


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside_file"
    outside.touch()
    link = tmp_path / "link"
    link.symlink_to(outside)
    with pytest.raises(PathEscapeError, match="escapes"):
        validate_path(tmp_path, "link")


def test_empty_string_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_path(tmp_path, "")


def test_repo_root_must_exist(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        validate_path(missing, "file.tex")
