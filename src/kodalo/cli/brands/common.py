"""Options, arguments and helpers the brand commands share."""

import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table
from rich.text import Text

from kodalo.cli import output
from kodalo.cli.state import State, get_state
from kodalo.core.brands.brand import (
    BrandError,
    BrandService,
)
from kodalo.core.brands.canvas import Canvas, CanvasError
from kodalo.core.brands.layout import Layout, LayoutError, LayoutSettings
from kodalo.core.brands.palette import PaletteError
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]
BrandArgument = Annotated[str, typer.Argument(help="Brand name or id.")]
CanvasArgument = Annotated[str, typer.Argument(help="Canvas name or id.")]
PaletteArgument = Annotated[str, typer.Argument(help="Palette name or id.")]
LayoutArgument = Annotated[str, typer.Argument(help="Layout name or id.")]
OutputOption = Annotated[
    Path | None, typer.Option("--output", "-o", dir_okay=False, help="Write to a file.")
]
InputFile = Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Exported JSON file.")]


@contextmanager
def open_service(ctx: typer.Context) -> Generator[BrandService]:
    """Open the database for one command, turning expected failures into exit code 1."""
    state = get_state(ctx)
    data_dir = state.data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield BrandService(database, data_dir)
    except (BrandError, CanvasError, LayoutError, PaletteError, StorageError) as error:
        output.error(str(error))
        for problem in getattr(error, "problems", [])[1:]:
            output.err_console.print(Text(f"  {problem}", style="red"))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def say(state: State, message: str) -> None:
    if not state.quiet:
        output.err_console.print(message)


def show_json(data: Any) -> None:
    output.console.print_json(data=data)


def size_text(canvas: Canvas) -> str:
    return f"{canvas.name} ({canvas.width}x{canvas.height})"


def read_payload(file: Path, kind: str) -> dict[str, Any]:
    """Read an exported JSON file, or exit with a clear message."""
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        output.error("That file is not valid JSON.")
        raise typer.Exit(code=1) from None
    if not isinstance(payload, dict):
        output.error(f"That file is not a Kodalo {kind} file.")
        raise typer.Exit(code=1)
    return payload


def write_payload(ctx: typer.Context, payload: dict[str, Any], file: Path | None) -> None:
    """Write an export to a file, or to the screen."""
    if file is None:
        show_json(payload)
        return
    file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    say(get_state(ctx), f"Wrote {file}")


def swatch(color: str) -> Text:
    """A small square of the exact color, followed by its hex value."""
    text = Text("  ", style=f"on {color}")
    text.append(f" {color}")
    return text


def group_table(title: str, *columns: str) -> Table:
    table = Table(title=title, title_justify="left", show_header=bool(columns))
    for column in columns or ("Setting", "Value"):
        table.add_column(column)
    return table


def layout_values(layout: Layout) -> dict[str, Any]:
    """The settings a layout decides, without its canvas (shown on its own line)."""
    return {
        key: value
        for key, value in layout.model_dump().items()
        if key in LayoutSettings.model_fields and key != "canvas_id"
    }
