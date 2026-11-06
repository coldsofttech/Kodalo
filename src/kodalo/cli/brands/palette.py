"""``brand palette`` commands: manage palettes."""

from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.brands.common import (
    InputFile,
    JsonOption,
    OutputOption,
    PaletteArgument,
    group_table,
    open_service,
    read_payload,
    say,
    show_json,
    swatch,
    write_payload,
)
from kodalo.cli.state import get_state
from kodalo.core.brands.palette import Palette

app = typer.Typer(
    help="Manage palettes: named sets of brand colors that new brands start from.",
    no_args_is_help=True,
)


def _palette_table(palette: Palette) -> Table:
    table = group_table(palette.name, "Color", "Light", "Dark")
    for name, pair in palette.colors.model_dump().items():
        table.add_row(name, swatch(pair["light"]), swatch(pair["dark"]))
    return table


@app.command("list")
def palette_list(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List palettes: the built-in ones first, then yours."""
    with open_service(ctx) as service:
        palettes = service.palettes.list_palettes()
    if json_output:
        show_json([p.model_dump(mode="json") for p in palettes])
        return
    table = Table(title="Palettes")
    for column in ("Name", "Type", "Primary", "Secondary", "Id"):
        table.add_column(column)
    for p in palettes:
        table.add_row(
            p.name,
            p.type,
            swatch(p.colors.primary.light),
            swatch(p.colors.secondary.light),
            p.id,
        )
    output.console.print(table)


@app.command("show")
def palette_show(
    ctx: typer.Context, name: PaletteArgument, json_output: JsonOption = False
) -> None:
    """Show every color of a palette."""
    with open_service(ctx) as service:
        palette = service.palettes.find(name)
    if json_output:
        show_json(palette.model_dump(mode="json"))
    else:
        output.console.print(_palette_table(palette))


@app.command("add")
def palette_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the new palette.")],
    from_brand: Annotated[
        str | None, typer.Option("--from-brand", help="Take the colors of this brand.")
    ] = None,
    from_palette: Annotated[
        str | None, typer.Option("--from-palette", help="Start from this palette.")
    ] = None,
) -> None:
    """Create a palette from a brand's colors or another palette (default: Midnight)."""
    if from_brand and from_palette:
        output.error("Use either --from-brand or --from-palette, not both.")
        raise typer.Exit(code=1)
    with open_service(ctx) as service:
        if from_brand:
            colors = service.find(from_brand).data.colors
        else:
            colors = service.palettes.find(from_palette or "midnight").colors
        palette = service.palettes.create(name, colors)
    say(get_state(ctx), f'Created "{palette.name}".')


@app.command("set")
def palette_set(
    ctx: typer.Context,
    name: PaletteArgument,
    path: Annotated[str, typer.Argument(help="Color, such as primary.light or text_alt.dark.")],
    value: Annotated[str, typer.Argument(help="New color, like #2563eb.")],
) -> None:
    """Change one color of a palette of your own."""
    with open_service(ctx) as service:
        service.palettes.set_color(service.palettes.find(name).id, path, value)
    say(get_state(ctx), f"{path} = {value}")


@app.command("rename")
def palette_rename(ctx: typer.Context, name: PaletteArgument, new_name: str) -> None:
    """Rename a palette of your own."""
    with open_service(ctx) as service:
        current = service.palettes.find(name)
        if current.name == new_name.strip():
            output.error(f'The palette is already named "{current.name}".')
            raise typer.Exit(code=1)
        palette = service.palettes.update(current.id, name=new_name)
    say(get_state(ctx), f'Renamed to "{palette.name}".')


@app.command("duplicate")
def palette_duplicate(ctx: typer.Context, name: PaletteArgument, new_name: str) -> None:
    """Copy a palette, built in or not, as a palette of your own."""
    with open_service(ctx) as service:
        palette = service.palettes.duplicate(service.palettes.find(name).id, new_name)
    say(get_state(ctx), f'Created "{palette.name}".')


@app.command("delete")
def palette_delete(
    ctx: typer.Context,
    name: PaletteArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a palette of your own. Brands made from it keep their colors."""
    with open_service(ctx) as service:
        palette = service.palettes.find(name)
        if not yes and not typer.confirm(f'Delete "{palette.name}"?', err=True):
            raise typer.Exit(code=1)
        service.palettes.delete(palette.id)
    say(get_state(ctx), f'Deleted "{palette.name}".')


@app.command("export")
def palette_export(ctx: typer.Context, name: PaletteArgument, file: OutputOption = None) -> None:
    """Export a palette as JSON (to a file, or to the screen)."""
    with open_service(ctx) as service:
        payload = service.palettes.export_palette(service.palettes.find(name).id)
    write_payload(ctx, payload, file)


@app.command("import")
def palette_import(
    ctx: typer.Context,
    file: InputFile,
    name: Annotated[str | None, typer.Option(help="Name for the new palette.")] = None,
) -> None:
    """Import a palette from a JSON file made by `palette export`."""
    payload = read_payload(file, "palette")
    with open_service(ctx) as service:
        palette = service.palettes.import_palette(payload, name=name)
    say(get_state(ctx), f'Imported "{palette.name}".')
