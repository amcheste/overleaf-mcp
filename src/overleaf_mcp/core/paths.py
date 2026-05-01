from pathlib import Path, PurePosixPath, PureWindowsPath

from overleaf_mcp.core.errors import PathEscapeError


def validate_path(repo_root: Path, target: str) -> Path:
    """Resolve target inside repo_root, rejecting escapes via absolute paths or symlinks.

    Accepts targets that do not yet exist (the caller may be creating a new file).
    """
    if not target:
        raise ValueError("target path cannot be empty")

    # Path.is_absolute() is platform-specific: on Windows '/etc/passwd' is
    # NOT absolute, on POSIX 'C:\\evil' is NOT absolute. Check both formats
    # so a malicious/wrong path from either world is rejected up-front
    # regardless of which OS the server runs on.
    if PurePosixPath(target).is_absolute() or PureWindowsPath(target).is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {target}")

    target_path = Path(target)

    canonical_root = repo_root.resolve(strict=True)
    candidate = (canonical_root / target_path).resolve(strict=False)

    try:
        candidate.relative_to(canonical_root)
    except ValueError:
        raise PathEscapeError(f"path escapes repo root: {target}") from None

    return candidate
