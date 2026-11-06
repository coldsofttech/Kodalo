"""``github`` commands: choose how Kodalo reaches GitHub. They parse input and show output only."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.github import (
    MODES,
    GitHubConnectivity,
    GitHubInvalidError,
    GitHubSettings,
    check_connection,
)
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

app = typer.Typer(
    help="Choose how Kodalo reaches GitHub: a local folder, the gh CLI or the web.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]


@contextmanager
def _connectivity(ctx: typer.Context) -> Iterator[GitHubConnectivity]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield GitHubConnectivity(database)
    except (GitHubInvalidError, StorageError) as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def _show(settings: GitHubSettings, as_json: bool) -> None:
    data = {
        "mode": settings.mode,
        "local_folder": settings.local_folder,
        "manifest_limit": settings.manifest_limit,
        "document_limit": settings.document_limit,
        "document_max_kb": settings.document_max_kb,
    }
    if as_json:
        output.console.print_json(data=data)
        return
    table = Table(show_header=False)
    table.add_row("Mode", settings.mode)
    table.add_row("Local folder", settings.local_folder or "-")
    table.add_row("Project files to read", str(settings.manifest_limit))
    table.add_row("Documents to read", str(settings.document_limit))
    table.add_row("Most of each document", f"{settings.document_max_kb} KB")
    output.console.print(table)


@app.command("show")
def show_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Show the current GitHub connectivity setting."""
    with _connectivity(ctx) as connectivity:
        _show(connectivity.get(), as_json)


@app.command("set")
def set_command(
    ctx: typer.Context,
    mode: Annotated[str, typer.Argument(help=f"One of: {', '.join(MODES)}.")],
    folder: Annotated[
        str | None,
        typer.Option("--folder", help="Folder holding your repositories (for local_folder)."),
    ] = None,
    manifest_limit: Annotated[
        int | None,
        typer.Option(
            "--manifest-limit",
            help="How many project files (package.json ...) to read from GitHub, 1 to 100.",
        ),
    ] = None,
    document_limit: Annotated[
        int | None,
        typer.Option(
            "--document-limit",
            help="How many documents (the README and the docs it links to) to read, 1 to 50.",
        ),
    ] = None,
    document_max_kb: Annotated[
        int | None,
        typer.Option(
            "--document-max-kb", help="How much of each document to read, in KB, 1 to 200."
        ),
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Choose the way to reach GitHub."""
    with _connectivity(ctx) as connectivity:
        _show(
            connectivity.save(mode, folder, manifest_limit, document_limit, document_max_kb),
            as_json,
        )


@app.command("check")
def check_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Check that the chosen way works. Exits with 1 when it does not."""
    with _connectivity(ctx) as connectivity:
        result = check_connection(connectivity.get())
    if as_json:
        output.console.print_json(
            data={"mode": result.mode, "ok": result.ok, "detail": result.detail}
        )
    else:
        output.console.print(f"{result.mode}: {'ok' if result.ok else 'failed'}. {result.detail}")
    if not result.ok:
        raise typer.Exit(code=1)
