"""``brand canvas`` commands: manage canvases."""

from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.brands.common import (
    CanvasArgument,
    InputFile,
    JsonOption,
    OutputOption,
    open_service,
    read_payload,
    say,
    show_json,
    write_payload,
)
from kodalo.cli.state import get_state

app = typer.Typer(
    help="Manage canvases: named slide sizes that brand layouts reuse.", no_args_is_help=True
)


@app.command("list")
def canvas_list(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List canvases: the built-in ones first, then yours."""
    with open_service(ctx) as service:
        canvases = service.canvases.list_canvases()
    if json_output:
        show_json([c.model_dump(mode="json") for c in canvases])
        return
    table = Table(title="Canvases")
    for column in ("Name", "Size", "Type", "Used by", "Id"):
        table.add_column(column)
    for c in canvases:
        table.add_row(c.name, f"{c.width}x{c.height}", c.type, ", ".join(c.used_by), c.id)
    output.console.print(table)


@app.command("show")
def canvas_show(ctx: typer.Context, name: CanvasArgument, json_output: JsonOption = False) -> None:
    """Show one canvas and the brands that use it."""
    with open_service(ctx) as service:
        canvas = service.canvases.find(name)
    if json_output:
        show_json(canvas.model_dump(mode="json"))
        return
    table = Table(title=canvas.name)
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("id", canvas.id)
    table.add_row("type", canvas.type)
    table.add_row("width", str(canvas.width))
    table.add_row("height", str(canvas.height))
    table.add_row("used by", ", ".join(canvas.used_by))
    output.console.print(table)


@app.command("add")
def canvas_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the new canvas.")],
    width: Annotated[int, typer.Argument(help="Width in pixels (200 to 4000).")],
    height: Annotated[int, typer.Argument(help="Height in pixels (200 to 4000).")],
) -> None:
    """Create a canvas."""
    with open_service(ctx) as service:
        canvas = service.canvases.create(name, width, height)
    say(get_state(ctx), f'Created "{canvas.name}" ({canvas.width}x{canvas.height}).')


@app.command("edit")
def canvas_edit(
    ctx: typer.Context,
    name: CanvasArgument,
    new_name: Annotated[str | None, typer.Option("--name", help="New name.")] = None,
    width: Annotated[int | None, typer.Option(help="New width in pixels.")] = None,
    height: Annotated[int | None, typer.Option(help="New height in pixels.")] = None,
) -> None:
    """Rename or resize a canvas. Every brand that uses it follows the change."""
    if new_name is None and width is None and height is None:
        output.error("Give at least one of --name, --width or --height.")
        raise typer.Exit(code=1)
    with open_service(ctx) as service:
        canvas = service.canvases.update(
            service.canvases.find(name).id, name=new_name, width=width, height=height
        )
    say(get_state(ctx), f'Updated "{canvas.name}" ({canvas.width}x{canvas.height}).')


@app.command("duplicate")
def canvas_duplicate(ctx: typer.Context, name: CanvasArgument, new_name: str) -> None:
    """Copy a canvas, built in or not, as a canvas of your own."""
    with open_service(ctx) as service:
        canvas = service.canvases.duplicate(service.canvases.find(name).id, new_name)
    say(get_state(ctx), f'Created "{canvas.name}" ({canvas.width}x{canvas.height}).')


@app.command("delete")
def canvas_delete(
    ctx: typer.Context,
    name: CanvasArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a canvas that no brand uses."""
    with open_service(ctx) as service:
        canvas = service.canvases.find(name)
        if not yes and not typer.confirm(f'Delete "{canvas.name}"?', err=True):
            raise typer.Exit(code=1)
        service.canvases.delete(canvas.id)
    say(get_state(ctx), f'Deleted "{canvas.name}".')


@app.command("export")
def canvas_export(ctx: typer.Context, name: CanvasArgument, file: OutputOption = None) -> None:
    """Export a canvas as JSON (to a file, or to the screen)."""
    with open_service(ctx) as service:
        payload = service.canvases.export_canvas(service.canvases.find(name).id)
    write_payload(ctx, payload, file)


@app.command("import")
def canvas_import(
    ctx: typer.Context,
    file: InputFile,
    name: Annotated[str | None, typer.Option(help="Name for the new canvas.")] = None,
) -> None:
    """Import a canvas from a JSON file made by `canvas export`."""
    payload = read_payload(file, "canvas")
    with open_service(ctx) as service:
        canvas = service.canvases.import_canvas(payload, name=name)
    say(get_state(ctx), f'Imported "{canvas.name}" ({canvas.width}x{canvas.height}).')
