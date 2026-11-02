"""Command line interface built on Typer and Rich. It only parses input and shows output."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table
from rich.text import Text

from kodalo.cli import brand, output, settings
from kodalo.cli.state import State, get_state
from kodalo.core import __version__
from kodalo.core.doctor import passed, run_checks

app = typer.Typer(
    name="kodalo",
    help="Example command line tool built on [bold]kodalo.core[/bold].",
    no_args_is_help=True,
    rich_markup_mode="rich",
    # run() reports errors briefly; Typer's own traceback would show local variables.
    pretty_exceptions_enable=False,
)

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]
app.add_typer(brand.app, name="brand")
app.add_typer(settings.app, name="settings")


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


@app.command()
def doctor(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """Diagnose the installation and the local data. Exits with 1 if a required check fails."""
    checks = run_checks(get_state(ctx).data_dir)
    healthy = passed(checks)
    if json_output:
        output.console.print_json(
            data={"healthy": healthy, "checks": [c.to_dict() for c in checks]}
        )
    else:
        table = Table(title="kodalo doctor")
        for column in ("Check", "Status", "Detail"):
            table.add_column(column)
        for check in checks:
            if check.ok:
                status = Text("ok", style="green")
            elif check.required:
                status = Text("FAIL", style="bold red")
            else:
                status = Text("warn", style="yellow")
            table.add_row(check.name, status, check.detail)
        output.console.print(table)
        if not healthy:
            output.error("One or more required checks failed.")
    if not healthy:
        raise typer.Exit(code=1)


def run() -> None:
    """Console script entry point: run the app and report unexpected errors briefly."""
    try:
        app()
    except Exception as exc:
        output.print_exception(exc)
        raise SystemExit(1) from exc
