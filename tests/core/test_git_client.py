import subprocess
from pathlib import Path

import pytest

from overleaf_mcp.core.errors import GitOperationError
from overleaf_mcp.core.git_client import GitClient


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    kwargs: dict = {"check": True, "capture_output": True, "text": True}
    if cwd is not None:
        kwargs["cwd"] = str(cwd)
    return subprocess.run(["git", *args], **kwargs)


@pytest.fixture
def tmp_bare_remote(tmp_path: Path) -> Path:
    bare = tmp_path / "bare.git"
    _git("init", "--bare", "-b", "main", str(bare))
    seed = tmp_path / "seed"
    _git("init", "-b", "main", str(seed))
    _git("config", "user.email", "seed@test", cwd=seed)
    _git("config", "user.name", "Seed", cwd=seed)
    (seed / "README.md").write_text("seed\n")
    _git("add", "README.md", cwd=seed)
    _git("commit", "-m", "seed", cwd=seed)
    _git("remote", "add", "origin", str(bare), cwd=seed)
    _git("push", "-u", "origin", "main", cwd=seed)
    return bare


@pytest.fixture
def tmp_repo_from_remote(
    tmp_path: Path, tmp_bare_remote: Path
) -> tuple[Path, GitClient]:
    repo = tmp_path / "work"
    gc = GitClient.clone(str(tmp_bare_remote), repo)
    _git("config", "user.email", "tester@test", cwd=repo)
    _git("config", "user.name", "Tester", cwd=repo)
    return repo, gc


def test_clone_creates_working_tree(tmp_path: Path, tmp_bare_remote: Path) -> None:
    dest = tmp_path / "clone"
    gc = GitClient.clone(str(tmp_bare_remote), dest)
    assert (dest / "README.md").read_text() == "seed\n"
    assert gc.repo_path == dest


def test_clone_fails_on_invalid_remote(tmp_path: Path) -> None:
    with pytest.raises(GitOperationError, match="clone failed"):
        GitClient.clone(str(tmp_path / "nonexistent"), tmp_path / "dest")


def test_working_tree_dirty_false_after_clone(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    _, gc = tmp_repo_from_remote
    assert gc.working_tree_dirty() is False


def test_working_tree_dirty_true_after_edit(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    (repo / "README.md").write_text("changed\n")
    assert gc.working_tree_dirty() is True


def test_write_file_and_read_file(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    target = repo / "sections" / "intro.tex"
    gc.write_file(target, "\\section{Intro}\n")
    assert gc.read_file(target) == "\\section{Intro}\n"


def test_commit_then_push_propagates_to_remote(
    tmp_path: Path,
    tmp_bare_remote: Path,
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    gc.write_file(repo / "note.tex", "hello\n")
    gc.commit("add note", "Tester <tester@example.com>")
    gc.push()

    verify = tmp_path / "verify"
    _git("clone", str(tmp_bare_remote), str(verify))
    assert (verify / "note.tex").read_text() == "hello\n"


def test_commit_sets_author_identity(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    gc.write_file(repo / "x.tex", "x")
    gc.commit("test", "Alice <alice@example.com>")
    result = _git("log", "-1", "--pretty=%an <%ae>", cwd=repo)
    assert result.stdout.strip() == "Alice <alice@example.com>"


def test_commit_rejects_invalid_author(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    _, gc = tmp_repo_from_remote
    with pytest.raises(ValueError, match="author must be"):
        gc.commit("msg", "no email here")


def test_pull_fetches_remote_changes(
    tmp_path: Path,
    tmp_bare_remote: Path,
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    other = tmp_path / "other"
    _git("clone", str(tmp_bare_remote), str(other))
    _git("config", "user.email", "other@test", cwd=other)
    _git("config", "user.name", "Other", cwd=other)
    (other / "new.tex").write_text("from other\n")
    _git("add", "new.tex", cwd=other)
    _git("commit", "-m", "add", cwd=other)
    _git("push", cwd=other)

    assert not (repo / "new.tex").exists()
    gc.pull()
    assert (repo / "new.tex").read_text() == "from other\n"


def test_list_files_returns_tracked_files(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    gc.write_file(repo / "a.tex", "a")
    gc.write_file(repo / "b.md", "b")
    gc.commit("add", "T <t@t.test>")
    files = gc.list_files()
    names = {p.name for p in files}
    assert names == {"README.md", "a.tex", "b.md"}


def test_list_files_filters_by_extension(
    tmp_repo_from_remote: tuple[Path, GitClient],
) -> None:
    repo, gc = tmp_repo_from_remote
    gc.write_file(repo / "a.tex", "a")
    gc.write_file(repo / "b.md", "b")
    gc.commit("add", "T <t@t.test>")
    assert {p.name for p in gc.list_files(extension=".tex")} == {"a.tex"}
    assert {p.name for p in gc.list_files(extension="tex")} == {"a.tex"}
