import click

from overleaf_mcp.cli.auth import auth
from overleaf_mcp.core.config import ProjectConfig, get_config_path, load_config, save_config
from overleaf_mcp.transports.stdio import main as _serve_main


@click.group()
@click.version_option()
def cli() -> None:
    """Overleaf MCP Server."""


cli.add_command(auth)


@cli.command()
def serve() -> None:
    """Run the MCP server over stdio."""
    _serve_main()


@cli.command()
def init() -> None:
    """Configure a project alias in the config file."""
    path = get_config_path()
    configs = load_config(path) if path.exists() else {}

    alias = click.prompt("Project alias (short nickname)").strip()
    if not alias:
        raise click.UsageError("alias cannot be empty")
    if alias in configs and not click.confirm(
        f"Alias '{alias}' already exists. Overwrite?", default=False
    ):
        click.echo("Aborted.")
        raise click.Abort()

    project_id = click.prompt("Overleaf project ID").strip()
    if not project_id:
        raise click.UsageError("project_id cannot be empty")

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
