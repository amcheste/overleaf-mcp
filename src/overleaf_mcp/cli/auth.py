import os
import sys

import click

from overleaf_mcp.core.config import get_config_path, load_config
from overleaf_mcp.core.credentials import (
    delete_token,
    has_token,
    store_token,
)
from overleaf_mcp.core.project import probe_remote


@click.group("auth")
def auth() -> None:
    """Manage Overleaf tokens in the OS keychain."""


@auth.command("add")
@click.option(
    "--project",
    default=None,
    help="Project alias; omit to store as the account-level fallback.",
)
@click.option(
    "--token-stdin",
    is_flag=True,
    default=False,
    help="Read the token from stdin instead of prompting.  Recommended "
         "for scripts: `printf '%s' \"$TOKEN\" | overleaf-mcp auth add ...`",
)
@click.option(
    "--token-from-env",
    "token_env_var",
    default=None,
    metavar="VAR_NAME",
    help="Read the token from the given environment variable.  Useful "
         "for CI: `OVERLEAF_TOKEN=... overleaf-mcp auth add ... "
         "--token-from-env OVERLEAF_TOKEN`",
)
def auth_add(
    project: str | None,
    token_stdin: bool,
    token_env_var: str | None,
) -> None:
    """Store an Overleaf token in the OS keychain.

    Interactive when run bare (prompts with hidden input).  Scriptable
    via --token-stdin (preferred) or --token-from-env.  Mutually
    exclusive: pass at most one of those two flags.

    There is no `--token VALUE` flag on purpose — values on the command
    line leak into the process listing (`ps`).
    """
    if token_stdin and token_env_var:
        raise click.UsageError(
            "use at most one of --token-stdin / --token-from-env"
        )

    if token_stdin:
        token = sys.stdin.read().strip()
    elif token_env_var:
        token = (os.environ.get(token_env_var) or "").strip()
        if not token:
            raise click.UsageError(
                f"environment variable {token_env_var!r} is empty or unset"
            )
    else:
        token = click.prompt("Overleaf token", hide_input=True).strip()

    if not token:
        raise click.UsageError("token cannot be empty")

    store_token(project, token)
    where = f"project '{project}'" if project else "account-level fallback"
    click.echo(f"Stored token for {where}.")

    if project is None:
        return

    path = get_config_path()
    configs = load_config(path) if path.exists() else {}
    if project not in configs:
        click.echo(
            f"Note: '{project}' is not in the config file. "
            f"Run 'overleaf-mcp init' to add it, then re-run auth."
        )
        return

    if probe_remote(configs[project].project_id, token):
        click.echo(f"Verified against project '{project}'.")
    else:
        click.echo(
            "Probe failed: the token may not have access to this project. "
            "If this is an account-level token, consider re-registering it "
            "without --project."
        )


@auth.command("remove")
@click.option(
    "--project",
    default=None,
    help="Project alias; omit to remove the account-level fallback.",
)
def auth_remove(project: str | None) -> None:
    """Remove an Overleaf token from the OS keychain."""
    where = f"project '{project}'" if project else "account-level fallback"
    if delete_token(project):
        click.echo(f"Removed token for {where}.")
    else:
        click.echo(f"No token stored for {where}.")


@auth.command("list")
def auth_list() -> None:
    """Show which aliases have tokens stored. Tokens themselves are never printed."""
    path = get_config_path()
    configs = load_config(path) if path.exists() else {}

    account_present = has_token(None)
    click.echo(f"Account-level fallback: {'set' if account_present else 'not set'}")

    if not configs:
        click.echo("(no projects configured)")
        return

    for alias in configs:
        state = "token set" if has_token(alias) else "no token (will use fallback)"
        click.echo(f"Project '{alias}': {state}")
