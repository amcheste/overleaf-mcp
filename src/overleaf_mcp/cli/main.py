import click


@click.group()
@click.version_option()
def cli() -> None:
    """Overleaf MCP Server."""
