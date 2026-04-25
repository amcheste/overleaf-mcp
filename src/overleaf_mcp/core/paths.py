from pathlib import Path

from overleaf_mcp.core.errors import PathEscapeError


def validate_path(repo_root: Path, target: str) -> Path:
    """Resolve target inside repo_root, rejecting escapes via absolute paths or symlinks.

    Accepts targets that do not yet exist (the caller may be creating a new file).
    """
    if not target:
        raise ValueError("target path cannot be empty")

    target_path = Path(target)
    if target_path.is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {target}")

    canonical_root = repo_root.resolve(strict=True)
    candidate = (canonical_root / target_path).resolve(strict=False)

    try:
        candidate.relative_to(canonical_root)
    except ValueError:
        raise PathEscapeError(f"path escapes repo root: {target}") from None

    return candidate
