import os
import re
import subprocess
from pathlib import Path

from overleaf_mcp.core.errors import GitOperationError


_AUTHOR_RE = re.compile(r"^(.+?)\s*<([^<>]+)>\s*$")


def _parse_author(author: str) -> tuple[str, str]:
    m = _AUTHOR_RE.match(author)
    if not m:
        raise ValueError(f"author must be 'Name <email>', got: {author!r}")
    return m.group(1).strip(), m.group(2).strip()


class GitClient:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    @classmethod
    def clone(cls, url: str, dest: Path) -> "GitClient":
        try:
            subprocess.run(
                ["git", "clone", url, str(dest)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"git clone failed: {e.stderr.strip()}") from e
        return cls(dest)

    def _run(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"git {args[0]} failed: {e.stderr.strip()}") from e

    def pull(self) -> None:
        self._run(["pull", "--ff-only"])

    def push(self) -> None:
        self._run(["push"])

    def commit(self, message: str, author: str) -> None:
        name, email = _parse_author(author)
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
        }
        self._run(["add", "-A"])
        self._run(["commit", "-m", message], env=env)

    def working_tree_dirty(self) -> bool:
        result = self._run(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def current_head(self) -> str:
        return self._run(["rev-parse", "HEAD"]).stdout.strip()

    def write_file(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def read_file(self, path: Path) -> str:
        return path.read_text()

    def delete_file(self, path: Path) -> None:
        """Remove a file from the working tree. The deletion gets staged on
        the next commit() (which runs `add -A`)."""
        path.unlink()

    def list_files(self, extension: str | None = None) -> list[Path]:
        result = self._run(["ls-files"])
        paths = [self.repo_path / line for line in result.stdout.splitlines() if line]
        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            paths = [p for p in paths if p.suffix == ext]
        return paths

    def last_commit_summary(self) -> str:
        """Short human-readable description of HEAD: short SHA, author,
        relative date, subject line."""
        return self._run(
            ["log", "-1", "--pretty=%h %an <%ae> (%ad)%n%s", "--date=relative"]
        ).stdout.strip()
