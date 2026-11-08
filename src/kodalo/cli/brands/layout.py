"""``brand layout`` commands: manage layouts."""

from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.brands.common import (
    InputFile,
    JsonOption,
    LayoutArgument,
    OutputOption,
    group_table,
    layout_values,
    open_service,
    read_payload,
    say,
    show_json,
    size_text,
    write_payload,
)
from kodalo.cli.state import get_state
from kodalo.core.brands.canvas import Canvas
from kodalo.core.brands.layout import Layout

app = typer.Typer(
    help="Manage layouts: named slide settings (canvas, margins, text, slide count) brands share.",
    no_args_is_help=True,
)


def _layout_table(layout: Layout, canvas: Canvas) -> Table:
    table = group_table(layout.name)
    table.add_row("id", layout.id)
    table.add_row("type", layout.type)
    table.add_row("canvas", f"{size_text(canvas)}  [{canvas.id}]")
    for name, value in layout_values(layout).items():
        table.add_row(name, str(value))
    table.add_row("used by", ", ".join(layout.used_by))
    return table


@app.command("list")
def layout_list(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List layouts: the built-in ones first, then yours."""
    with open_service(ctx) as service:
        layouts = service.layouts.list_layouts()
        canvases = {c.id: c for c in service.canvases.list_canvases()}
    if json_output:
        show_json([lay.model_dump(mode="json") for lay in layouts])
        return
    table = Table(title="Layouts")
    for column in ("Name", "Type", "Canvas", "Slides", "Used by", "Id"):
        table.add_column(column)
    for lay in layouts:
        table.add_row(
            lay.name,
            lay.type,
            size_text(canvases[lay.canvas_id]),
            str(lay.slides_count),
            ", ".join(lay.used_by),
            lay.id,
        )
    output.console.print(table)


@app.command("show")
def layout_show(ctx: typer.Context, name: LayoutArgument, json_output: JsonOption = False) -> None:
    """Show every setting of a layout and the brands that use it."""
    with open_service(ctx) as service:
        layout = service.layouts.find(name)
        canvas = service.canvases.get(layout.canvas_id)
    if json_output:
        show_json(layout.model_dump(mode="json"))
    else:
        output.console.print(_layout_table(layout, canvas))


@app.command("add")
def layout_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the new layout.")],
    from_layout: Annotated[
        str | None, typer.Option("--from-layout", help="Start from this layout (default: Default).")
    ] = None,
) -> None:
    """Create a layout from another layout. Change it afterwards with `layout set`."""
    with open_service(ctx) as service:
        source = service.layouts.find(from_layout or "Default")
        layout = service.layouts.duplicate(source.id, name)
    say(get_state(ctx), f'Created "{layout.name}".')


@app.command("set")
def layout_set(
    ctx: typer.Context,
    name: LayoutArgument,
    path: Annotated[str, typer.Argument(help="Setting, such as margin_top or slides_count.")],
    value: Annotated[str, typer.Argument(help="New value. For canvas_id: a canvas name or id.")],
) -> None:
    """Change one setting of a layout of your own. Brands using it follow the change."""
    with open_service(ctx) as service:
        service.layouts.change(service.layouts.find(name).id, path, value)
    say(get_state(ctx), f"{path} = {value}")


@app.command("settings")
def layout_settings(
    ctx: typer.Context, name: LayoutArgument, json_output: JsonOption = False
) -> None:
    """List the settings that `layout set` accepts, with their values."""
    with open_service(ctx) as service:
        layout = service.layouts.find(name)
    values = {"canvas_id": layout.canvas_id, **layout_values(layout)}
    if json_output:
        show_json(values)
        return
    table = Table(title="Layout settings")
    table.add_column("Setting")
    table.add_column("Value")
    for key, value in values.items():
        table.add_row(key, str(value))
    output.console.print(table)


@app.command("rename")
def layout_rename(ctx: typer.Context, name: LayoutArgument, new_name: str) -> None:
    """Rename a layout of your own."""
    with open_service(ctx) as service:
        current = service.layouts.find(name)
        if current.name == new_name.strip():
            output.error(f'The layout is already named "{current.name}".')
            raise typer.Exit(code=1)
        layout = service.layouts.update(current.id, name=new_name)
    say(get_state(ctx), f'Renamed to "{layout.name}".')


@app.command("duplicate")
def layout_duplicate(ctx: typer.Context, name: LayoutArgument, new_name: str) -> None:
    """Copy a layout, built in or not, as a layout of your own."""
    with open_service(ctx) as service:
        layout = service.layouts.duplicate(service.layouts.find(name).id, new_name)
    say(get_state(ctx), f'Created "{layout.name}".')


@app.command("delete")
def layout_delete(
    ctx: typer.Context,
    name: LayoutArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a layout that no brand uses."""
    with open_service(ctx) as service:
        layout = service.layouts.find(name)
        if not yes and not typer.confirm(f'Delete "{layout.name}"?', err=True):
            raise typer.Exit(code=1)
        service.layouts.delete(layout.id)
    say(get_state(ctx), f'Deleted "{layout.name}".')


@app.command("export")
def layout_export(ctx: typer.Context, name: LayoutArgument, file: OutputOption = None) -> None:
    """Export a layout, with its canvas, as JSON (to a file, or to the screen)."""
    with open_service(ctx) as service:
        payload = service.layouts.export_layout(service.layouts.find(name).id)
    write_payload(ctx, payload, file)


@app.command("import")
def layout_import(
    ctx: typer.Context,
    file: InputFile,
    name: Annotated[str | None, typer.Option(help="Name for the new layout.")] = None,
) -> None:
    """Import a layout from a JSON file made by `layout export`."""
    payload = read_payload(file, "layout")
    with open_service(ctx) as service:
        layout = service.layouts.import_layout(payload, name=name)
    say(get_state(ctx), f'Imported "{layout.name}".')
