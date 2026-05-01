import shutil

import click

from overleaf_mcp.cli.auth import auth
from overleaf_mcp.cli.project import project
from overleaf_mcp.core.config import ProjectConfig, get_config_path, load_config, save_config
from overleaf_mcp.core.credentials import resolve_token
from overleaf_mcp.core.errors import TokenNotFoundError
from overleaf_mcp.core.project import get_git_author, get_repo_path, probe_remote
from overleaf_mcp.transports.stdio import main as _serve_main


@click.group()
@click.version_option(package_name="overleaf-mcp-server")
def cli() -> None:
    """Overleaf MCP Server."""


cli.add_command(auth)
cli.add_command(project)


@cli.command()
def serve() -> None:
    """Run the MCP server over stdio."""
    _serve_main()


@cli.command()
@click.option(
    "--alias",
    "alias_opt",
    default=None,
    help="Project alias (short nickname).  Skips the prompt when set.",
)
@click.option(
    "--project-id",
    "project_id_opt",
    default=None,
    help="Overleaf project ID.  Skips the prompt when set.",
)
@click.option(
    "--display-name",
    "display_name_opt",
    default=None,
    help="Optional display name.  Use \"\" to clear; skips the prompt when set.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing alias without prompting for confirmation.",
)
def init(
    alias_opt: str | None,
    project_id_opt: str | None,
    display_name_opt: str | None,
    force: bool,
) -> None:
    """Configure a project alias in the config file.

    Interactive when called bare.  Passing --alias engages fully
    non-interactive mode: --project-id becomes required, --display-name
    defaults to empty, and an existing alias requires --force to
    overwrite (no confirm prompt).
    """
    path = get_config_path()
    configs = load_config(path) if path.exists() else {}

    # Non-interactive mode is signalled by --alias being set. In that
    # mode we never prompt for anything — missing required flags are
    # immediate UsageError, missing optional flags use empty defaults.
    non_interactive = alias_opt is not None

    if non_interactive:
        alias = alias_opt.strip()
    else:
        alias = click.prompt("Project alias (short nickname)").strip()
    if not alias:
        raise click.UsageError("alias cannot be empty")

    if alias in configs:
        if force:
            pass  # silently overwrite
        elif non_interactive:
            raise click.UsageError(
                f"alias '{alias}' already exists; pass --force to overwrite"
            )
        elif not click.confirm(
            f"Alias '{alias}' already exists. Overwrite?", default=False
        ):
            click.echo("Aborted.")
            raise click.Abort()

    if non_interactive:
        if project_id_opt is None:
            raise click.UsageError(
                "--project-id is required when --alias is passed"
            )
        project_id = project_id_opt.strip()
    else:
        project_id = (
            project_id_opt.strip()
            if project_id_opt is not None
            else click.prompt("Overleaf project ID").strip()
        )
    if not project_id:
        raise click.UsageError("project_id cannot be empty")

    if non_interactive or display_name_opt is not None:
        display_name = (display_name_opt or "").strip()
    else:
        display_name = click.prompt(
            "Display name (optional)", default="", show_default=False
        ).strip()

    configs[alias] = ProjectConfig(
        alias=alias,
        project_id=project_id,
        display_name=display_name or None,
    )
    save_config(path, configs)
    click.echo(f"Configured '{alias}' in {path}.")
    click.echo(f"Next: overleaf-mcp auth add --project {alias}")


@cli.command()
def doctor() -> None:
    """Diagnose the server setup and report pass/fail per check."""
    failures = 0

    path = get_config_path()
    click.echo(f"Config: {path}")
    if not path.exists():
        click.echo("  FAIL: config file does not exist. Run 'overleaf-mcp init'.")
        raise click.exceptions.Exit(1)
    try:
        configs = load_config(path)
    except Exception as exc:
        click.echo(f"  FAIL: could not parse config ({exc}).")
        raise click.exceptions.Exit(1) from exc
    click.echo(f"  ok: loaded {len(configs)} project(s)")

    git_bin = shutil.which("git")
    click.echo(f"Git binary: {git_bin or 'NOT FOUND'}")
    if not git_bin:
        click.echo("  FAIL: git is not on PATH.")
        failures += 1

    try:
        click.echo(f"Git author: {get_git_author()}")
    except RuntimeError as exc:
        click.echo(f"Git author: FAIL: {exc}")
        failures += 1

    for alias, cfg in configs.items():
        click.echo(f"\nProject '{alias}':")
        try:
            token = resolve_token(alias)
            click.echo("  Token: ok")
        except TokenNotFoundError:
            click.echo(
                f"  Token: FAIL (run 'overleaf-mcp auth add --project {alias}')"
            )
            failures += 1
            continue

        if probe_remote(cfg.project_id, token):
            click.echo("  Remote: ok")
        else:
            click.echo("  Remote: FAIL (git ls-remote did not succeed)")
            failures += 1

        repo_path = get_repo_path(alias)
        if repo_path.exists():
            click.echo(f"  Clone: ok ({repo_path})")
        else:
            click.echo(
                f"  Clone: missing — run 'overleaf-mcp project clone {alias}'"
            )

    if failures:
        click.echo(f"\n{failures} check(s) failed.")
        raise click.exceptions.Exit(1)
    click.echo("\nAll checks passed.")
