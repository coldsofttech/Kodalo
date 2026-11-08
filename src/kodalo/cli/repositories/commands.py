"""``repositories check``, ``list``, ``show`` and ``remove``."""

import dataclasses
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.repositories.common import JsonOption, RepoArgument, open_services
from kodalo.cli.repositories.show import show_repo
from kodalo.cli.state import get_state
from kodalo.core.studio import validate_source


def check_command(
    ctx: typer.Context,
    value: Annotated[
        str, typer.Argument(help="A folder (local_folder mode) or a GitHub repository address.")
    ],
    as_json: JsonOption = False,
) -> None:
    """Check a folder or address against the GitHub mode. Exits with 1 when it is not valid."""
    with open_services(ctx) as (settings, *_):
        source = validate_source(settings, value)
    if as_json:
        output.console.print_json(data=dataclasses.asdict(source))
    else:
        output.console.print(f"{source.name}: {source.value}")


def list_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """List the added repositories."""
    with open_services(ctx) as (_, repos, *_):
        items = repos.list_repos()
    if as_json:
        data = [dataclasses.asdict(i) for i in items]
        for entry in data:
            del entry["paths"]  # only used while reading
        output.console.print_json(data=data)
        return
    if not items:
        output.console.print("No repositories yet. Add one with: kodalo repositories add <address>")
        return
    table = Table("Repository", "Branch", "License", "Last read", "Id")
    for item in items:
        table.add_row(
            f"{item.owner}/{item.name}",
            item.default_branch or "-",
            item.license or "-",
            item.last_scanned_at or "-",
            item.id,
        )
    output.console.print(table)


def show_command(ctx: typer.Context, repo_id: RepoArgument, as_json: JsonOption = False) -> None:
    """Show an added repository."""
    with open_services(ctx) as (_, repos, *_):
        info = repos.get(repo_id)
    show_repo(info, as_json)


def remove_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Remove a repository and everything saved about it (analysis, features, ideas)."""
    with open_services(ctx) as (_, repos, *_):
        info = repos.get(repo_id)
        name = f"{info.owner}/{info.name}"
        if not yes and not typer.confirm(f'Remove "{name}"?', err=True):
            raise typer.Exit(code=1)
        repos.remove(repo_id)
    if not get_state(ctx).quiet:
        output.err_console.print(f'Removed "{name}".')
