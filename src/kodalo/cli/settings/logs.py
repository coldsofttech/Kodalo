"""``logs`` commands: choose how much Kodalo logs and how long it keeps the files."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.settings.logs import (
    LEVELS,
    MAX_RETENTION_DAYS,
    MIN_RETENTION_DAYS,
    LogConfig,
    LogSettings,
    LogsInvalidError,
    configure_file_logging,
    logs_dir,
)
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

app = typer.Typer(
    help="Choose the log level and how long log files are kept.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]


@contextmanager
def _settings(ctx: typer.Context) -> Generator[tuple[LogSettings, Path]]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield LogSettings(database), data_dir
    except (LogsInvalidError, StorageError) as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def _show(config: LogConfig, folder: Path, as_json: bool) -> None:
    location = str(logs_dir(folder))
    if as_json:
        output.console.print_json(
            data={
                "level": config.level,
                "retention_days": config.retention_days,
                "folder": location,
            }
        )
        return
    table = Table(show_header=False)
    table.add_row("Level", config.level)
    table.add_row("Retention", f"{config.retention_days} days")
    table.add_row("Folder", location)
    output.console.print(table)


@app.command("show")
def show_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Show the log level, retention and the folder the logs are written to."""
    with _settings(ctx) as (settings, folder):
        _show(settings.get(), folder, as_json)


@app.command("set")
def set_command(
    ctx: typer.Context,
    level: Annotated[
        str | None,
        typer.Option("--level", help=f"One of: {', '.join(LEVELS)}. Default: INFO."),
    ] = None,
    retention_days: Annotated[
        int | None,
        typer.Option(
            "--retention",
            help=f"Days to keep log files, {MIN_RETENTION_DAYS} to {MAX_RETENTION_DAYS}. "
            "Default: 90.",
        ),
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Change the log level and/or how many days of logs are kept."""
    with _settings(ctx) as (settings, folder):
        config = settings.save(level, retention_days)
        configure_file_logging(folder, config)
        _show(config, folder, as_json)
