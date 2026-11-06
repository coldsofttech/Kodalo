"""Command line interface built on Typer and Rich. It only parses input and shows output."""

from pathlib import Path
from typing import Annotated

import typer

from kodalo.cli import brand, doctor, output, settings, studio
from kodalo.cli.state import State
from kodalo.core import __version__
from kodalo.core.ai import purge_expired_history
from kodalo.core.storage import default_data_dir

app = typer.Typer(
    name="kodalo",
    help="Example command line tool built on [bold]kodalo.core[/bold].",
    no_args_is_help=True,
    rich_markup_mode="rich",
    # run() reports errors briefly; Typer's own traceback would show local variables.
    pretty_exceptions_enable=False,
)

app.add_typer(brand.app, name="brand")
app.add_typer(settings.app, name="settings")
app.add_typer(studio.app, name="studio")
app.command()(doctor.doctor)


def _show_version(value: bool) -> None:
    if value:
        output.console.print(f"kodalo {__version__}")
        raise typer.Exit


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_show_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show extra detail."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Only show errors."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable colored output."),
    ] = False,
    data_dir: Annotated[
        Path | None,
        typer.Option(
            "--data-dir",
            file_okay=False,
            help="Folder for the database and logos. Default: %LOCALAPPDATA%/Kodalo.",
        ),
    ] = None,
) -> None:
    """Options that apply to every command."""
    if verbose and quiet:
        raise typer.BadParameter("--verbose and --quiet cannot be used together.")
    output.configure(no_color=no_color, verbose=verbose)
    ctx.obj = State(verbose=verbose, quiet=quiet, data_dir=data_dir)
    purge_expired_history(data_dir or default_data_dir())


def run() -> None:
    """Console script entry point: run the app and report unexpected errors briefly."""
    try:
        app()
    except Exception as exc:
        output.print_exception(exc)
        raise SystemExit(1) from exc
