import click

from overleaf_mcp.transports.stdio import main as _serve_main


@click.group()
@click.version_option()
def cli() -> None:
    """Overleaf MCP Server."""


@cli.command()
def serve() -> None:
    """Run the MCP server over stdio."""
    _serve_main()
