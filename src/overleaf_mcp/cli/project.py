import click

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.credentials import resolve_token
from overleaf_mcp.core.errors import GitOperationError, TokenNotFoundError
from overleaf_mcp.core.project import clone_with_token, get_repo_path


@click.group("project")
def project() -> None:
    """Project lifecycle commands (clone, etc.)."""


@project.command("clone")
@click.argument("alias")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="If a clone already exists at the cache path, remove it and re-clone.",
)
def project_clone(alias: str, force: bool) -> None:
    """Clone the Overleaf project for ALIAS into the local cache.

    Uses the same token-aware askpass flow as probe_remote, so the
    Overleaf token never appears on the subprocess command line and
    isn't recorded in the cloned repo's git config.
    """
    path = get_config_path()
    if not path.exists():
        raise click.UsageError("no config file; run 'overleaf-mcp init' first")

    configs = load_config(path)
    if alias not in configs:
        raise click.UsageError(
            f"unknown project alias '{alias}'. Configured: {sorted(configs)}"
        )

    cfg = configs[alias]
    repo_path = get_repo_path(alias)

    if repo_path.exists():
        if not force:
            click.echo(f"Already cloned at {repo_path}.")
            click.echo("Pass --force to remove and re-clone.")
            return
        import shutil

        shutil.rmtree(repo_path)

    try:
        token = resolve_token(alias)
    except TokenNotFoundError as exc:
        raise click.UsageError(str(exc)) from exc

    click.echo(f"Cloning {cfg.project_id} into {repo_path}...")
    try:
        clone_with_token(cfg.project_id, token, repo_path)
    except GitOperationError as exc:
        raise click.UsageError(str(exc)) from exc

    click.echo(f"Cloned '{alias}' to {repo_path}.")
