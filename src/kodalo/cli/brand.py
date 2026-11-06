"""``brand`` commands: manage brand profiles. They parse input and show output only."""

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
    Brand,
    BrandError,
    BrandService,
    ContrastResult,
    check_colors,
    list_paths,
    set_value,
)
from kodalo.core.brands.canvas import Canvas, CanvasError
from kodalo.core.brands.layout import Layout, LayoutError, LayoutSettings
from kodalo.core.brands.palette import Palette, PaletteError
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

app = typer.Typer(
    help="Manage brand profiles: colors, fonts, logo and layout.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
logo_app = typer.Typer(help="Set or remove a profile's logo.", no_args_is_help=True)
app.add_typer(logo_app, name="logo", rich_help_panel="Change a profile")
settings_app = typer.Typer(help="List and change the settings of a profile.", no_args_is_help=True)
app.add_typer(settings_app, name="settings", rich_help_panel="Change a profile")
layout_app = typer.Typer(
    help="Manage layouts: named slide settings (canvas, margins, text, slide count) brands share.",
    no_args_is_help=True,
)
app.add_typer(layout_app, name="layout", rich_help_panel="Layouts")
palette_app = typer.Typer(
    help="Manage palettes: named sets of brand colors that new brands start from.",
    no_args_is_help=True,
)
app.add_typer(palette_app, name="palette", rich_help_panel="Palettes")
canvas_app = typer.Typer(
    help="Manage canvases: named slide sizes that brand layouts reuse.", no_args_is_help=True
)
app.add_typer(canvas_app, name="canvas", rich_help_panel="Canvases")

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
def _service(ctx: typer.Context) -> Generator[BrandService]:
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


def _say(state: State, message: str) -> None:
    if not state.quiet:
        output.err_console.print(message)


def _show_json(data: Any) -> None:
    output.console.print_json(data=data)


def _size(canvas: Canvas) -> str:
    return f"{canvas.name} ({canvas.width}x{canvas.height})"


def _contrast_table(results: list[ContrastResult]) -> Table:
    table = Table(title="Contrast")
    for column in ("Color", "On", "Mode", "Ratio", "Needs", "Result"):
        table.add_column(column)
    for r in results:
        verdict = Text("pass", style="green") if r.passes else Text("FAIL", style="bold red")
        table.add_row(
            r.foreground, r.background, r.mode, f"{r.ratio:.2f}", f"{r.minimum:.1f}", verdict
        )
    return table


@app.command("list", rich_help_panel="Profiles")
def list_command(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List brand profiles."""
    with _service(ctx) as service:
        brands = service.list_brands()
    if json_output:
        _show_json(
            [
                {
                    "id": b.id,
                    "name": b.name,
                    "is_default": b.is_default,
                    "layout": {"id": b.layout.id, "name": b.layout.name},
                    "canvas": {
                        "id": b.canvas.id,
                        "name": b.canvas.name,
                        "width": b.canvas.width,
                        "height": b.canvas.height,
                    },
                }
                for b in brands
            ]
        )
        return
    if not brands:
        _say(get_state(ctx), "No brands yet. Create one with: brand create NAME")
        return
    table = Table(title="Brands")
    for column in ("Name", "Default", "Layout", "Canvas", "Id"):
        table.add_column(column)
    for b in brands:
        table.add_row(b.name, "yes" if b.is_default else "", b.layout.name, _size(b.canvas), b.id)
    output.console.print(table)


def _read_payload(file: Path, kind: str) -> dict[str, Any]:
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


def _write_payload(ctx: typer.Context, payload: dict[str, Any], file: Path | None) -> None:
    """Write an export to a file, or to the screen."""
    if file is None:
        _show_json(payload)
        return
    file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _say(get_state(ctx), f"Wrote {file}")


def _swatch(color: str) -> Text:
    """A small square of the exact color, followed by its hex value."""
    text = Text("  ", style=f"on {color}")
    text.append(f" {color}")
    return text


def _group(title: str, *columns: str) -> Table:
    table = Table(title=title, title_justify="left", show_header=bool(columns))
    for column in columns or ("Setting", "Value"):
        table.add_column(column)
    return table


def _layout_settings(layout: Layout) -> dict[str, Any]:
    """The settings a layout decides, without its canvas (shown on its own line)."""
    return {
        key: value
        for key, value in layout.model_dump().items()
        if key in LayoutSettings.model_fields and key != "canvas_id"
    }


def _show_brand(brand: Brand) -> None:
    data = brand.data
    general = _group(f"{brand.name}{' (default)' if brand.is_default else ''}")
    general.add_row("name", brand.name)
    general.add_row("default", "yes" if brand.is_default else "no")
    general.add_row("id", brand.id)
    general.add_row("created", brand.created_at)
    general.add_row("updated", brand.updated_at)
    colors = _group("Colors", "Color", "Light", "Dark")
    for name, pair in data.colors.model_dump().items():
        colors.add_row(name, _swatch(pair["light"]), _swatch(pair["dark"]))
    fonts = _group("Fonts", "Font", "Family", "Source")
    for name, font in data.fonts.model_dump().items():
        fonts.add_row(name, font["family"], font["source"])
    logo = _group("Logo")
    for name, value in data.logo.model_dump().items():
        logo.add_row(name, "" if value is None else str(value))
    layout = _group("Layout")
    layout.add_row("layout", f"{brand.layout.name}  [{brand.layout.id}]")
    layout.add_row("canvas", f"{_size(brand.canvas)}  [{brand.canvas.id}]")
    for name, value in _layout_settings(brand.layout).items():
        layout.add_row(name, str(value))
    for table in (general, colors, fonts, logo, layout):
        output.console.print(table)


@app.command(rich_help_panel="Profiles")
def show(ctx: typer.Context, name: BrandArgument, json_output: JsonOption = False) -> None:
    """Show every setting of a profile."""
    with _service(ctx) as service:
        brand = service.find(name)
    if json_output:
        _show_json(brand.model_dump(mode="json"))
    else:
        _show_brand(brand)


@app.command(rich_help_panel="Profiles")
def create(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the new profile.")],
    palette: Annotated[
        str, typer.Option(help="Palette name or id to start from. See: brand palette list")
    ] = "midnight",
    make_default: Annotated[bool, typer.Option("--default", help="Make it the default.")] = False,
) -> None:
    """Create a profile from a palette."""
    with _service(ctx) as service:
        brand = service.create(name, service.starter(palette))
        if make_default:
            brand = service.set_default(brand.id)
    _say(get_state(ctx), f'Created "{brand.name}".')


@app.command(rich_help_panel="Profiles")
def rename(ctx: typer.Context, name: BrandArgument, new_name: str) -> None:
    """Rename a profile."""
    with _service(ctx) as service:
        current = service.find(name)
        if current.name == new_name.strip():
            output.error(f'The brand is already named "{current.name}".')
            raise typer.Exit(code=1)
        brand = service.update(current.id, name=new_name)
    _say(get_state(ctx), f'Renamed to "{brand.name}".')


@app.command(rich_help_panel="Profiles")
def delete(
    ctx: typer.Context,
    name: BrandArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a profile and its logo files."""
    with _service(ctx) as service:
        brand = service.find(name)
        if not yes and not typer.confirm(f'Delete "{brand.name}"?', err=True):
            raise typer.Exit(code=1)
        service.delete(brand.id)
    _say(get_state(ctx), f'Deleted "{brand.name}".')


@app.command("default", rich_help_panel="Profiles")
def default_command(ctx: typer.Context, name: BrandArgument) -> None:
    """Make a profile the default."""
    with _service(ctx) as service:
        brand = service.set_default(service.find(name).id)
    _say(get_state(ctx), f'"{brand.name}" is now the default.')


@app.command(rich_help_panel="Profiles")
def duplicate(ctx: typer.Context, name: BrandArgument, new_name: str) -> None:
    """Copy a profile, including its logo files."""
    with _service(ctx) as service:
        brand = service.duplicate(service.find(name).id, new_name)
    _say(get_state(ctx), f'Created "{brand.name}".')


@settings_app.command("set")
def settings_set(
    ctx: typer.Context,
    name: BrandArgument,
    path: Annotated[str, typer.Argument(help="Setting, such as colors.primary.light.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Change one setting. Run `brand settings list NAME` to see the paths you can use."""
    with _service(ctx) as service:
        brand = service.find(name)
        data = set_value(brand.data, path, value)
        service.update(brand.id, data=data)
    _say(get_state(ctx), f"{path} = {value}")


@settings_app.command("list")
def settings_list(ctx: typer.Context, name: BrandArgument, json_output: JsonOption = False) -> None:
    """List the settings of a profile that `settings set` accepts, with their values."""
    with _service(ctx) as service:
        data = service.find(name).data
    dumped = data.model_dump()
    values: dict[str, Any] = {}
    for path in list_paths(data):
        node: Any = dumped
        for part in path.split("."):
            node = node[part]
        values[path] = node
    if json_output:
        _show_json(values)
        return
    table = Table(title="Settings")
    table.add_column("Path")
    table.add_column("Value")
    for path, value in values.items():
        table.add_row(path, "" if value is None else str(value))
    output.console.print(table)


@app.command(rich_help_panel="Check")
def check(
    ctx: typer.Context,
    name: BrandArgument,
    strict: Annotated[
        bool, typer.Option("--strict", help="Exit with 1 if any check fails.")
    ] = False,
    json_output: JsonOption = False,
) -> None:
    """Check the contrast of a profile's colors."""
    with _service(ctx) as service:
        results = check_colors(service.find(name).data.colors)
    if json_output:
        _show_json(
            [
                {
                    "color": r.foreground,
                    "on": r.background,
                    "mode": r.mode,
                    "ratio": r.ratio,
                    "minimum": r.minimum,
                    "passes": r.passes,
                }
                for r in results
            ]
        )
    else:
        output.console.print(_contrast_table(results))
    if strict and not all(r.passes for r in results):
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Look up")
def fonts(
    ctx: typer.Context,
    system: Annotated[
        bool, typer.Option("--system/--bundled", help="Include installed fonts (default) or not.")
    ] = True,
    json_output: JsonOption = False,
) -> None:
    """List the fonts a profile can use (the font catalogue)."""
    with _service(ctx) as service:
        items = service.fonts.list_fonts(system=system)
    if json_output:
        _show_json(
            [{"family": f.family, "category": f.category, "source": f.source} for f in items]
        )
        return
    table = Table(title="Fonts")
    for column in ("Family", "Category", "Source"):
        table.add_column(column)
    for f in items:
        table.add_row(f.family, f.category, f.source)
    output.console.print(table)


@app.command("export", rich_help_panel="Share")
def export_command(
    ctx: typer.Context,
    name: BrandArgument,
    file: Annotated[
        Path | None, typer.Option("--output", "-o", dir_okay=False, help="Write to a file.")
    ] = None,
) -> None:
    """Export a profile, with its logos, as JSON (to a file, or to the screen)."""
    with _service(ctx) as service:
        payload = service.export_profile(service.find(name).id)
    _write_payload(ctx, payload, file)


@app.command("import", rich_help_panel="Share")
def import_command(
    ctx: typer.Context,
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Exported JSON file.")],
    name: Annotated[str | None, typer.Option(help="Name for the new profile.")] = None,
) -> None:
    """Import a profile from a JSON file made by `export`."""
    payload = _read_payload(file, "brand")
    with _service(ctx) as service:
        brand = service.import_profile(payload, name=name)
    _say(get_state(ctx), f'Imported "{brand.name}".')


@logo_app.command("set")
def logo_set(
    ctx: typer.Context,
    name: BrandArgument,
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="PNG or SVG file.")],
    dark: Annotated[bool, typer.Option("--dark", help="Use it as the dark-mode logo.")] = False,
) -> None:
    """Set a profile's logo from a PNG or SVG file."""
    with _service(ctx) as service:
        service.set_logo(service.find(name).id, file.read_bytes(), dark=dark)
    _say(get_state(ctx), "Logo set.")


@logo_app.command("remove")
def logo_remove(
    ctx: typer.Context,
    name: BrandArgument,
    dark: Annotated[bool, typer.Option("--dark", help="Remove the dark-mode logo.")] = False,
) -> None:
    """Remove a profile's logo."""
    with _service(ctx) as service:
        service.remove_logo(service.find(name).id, dark=dark)
    _say(get_state(ctx), "Logo removed.")


@canvas_app.command("list")
def canvas_list(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List canvases: the built-in ones first, then yours."""
    with _service(ctx) as service:
        canvases = service.canvases.list_canvases()
    if json_output:
        _show_json([c.model_dump(mode="json") for c in canvases])
        return
    table = Table(title="Canvases")
    for column in ("Name", "Size", "Type", "Used by", "Id"):
        table.add_column(column)
    for c in canvases:
        table.add_row(c.name, f"{c.width}x{c.height}", c.type, ", ".join(c.used_by), c.id)
    output.console.print(table)


@canvas_app.command("show")
def canvas_show(ctx: typer.Context, name: CanvasArgument, json_output: JsonOption = False) -> None:
    """Show one canvas and the brands that use it."""
    with _service(ctx) as service:
        canvas = service.canvases.find(name)
    if json_output:
        _show_json(canvas.model_dump(mode="json"))
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


@canvas_app.command("add")
def canvas_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the new canvas.")],
    width: Annotated[int, typer.Argument(help="Width in pixels (200 to 4000).")],
    height: Annotated[int, typer.Argument(help="Height in pixels (200 to 4000).")],
) -> None:
    """Create a canvas."""
    with _service(ctx) as service:
        canvas = service.canvases.create(name, width, height)
    _say(get_state(ctx), f'Created "{canvas.name}" ({canvas.width}x{canvas.height}).')


@canvas_app.command("edit")
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
    with _service(ctx) as service:
        canvas = service.canvases.update(
            service.canvases.find(name).id, name=new_name, width=width, height=height
        )
    _say(get_state(ctx), f'Updated "{canvas.name}" ({canvas.width}x{canvas.height}).')


@canvas_app.command("duplicate")
def canvas_duplicate(ctx: typer.Context, name: CanvasArgument, new_name: str) -> None:
    """Copy a canvas, built in or not, as a canvas of your own."""
    with _service(ctx) as service:
        canvas = service.canvases.duplicate(service.canvases.find(name).id, new_name)
    _say(get_state(ctx), f'Created "{canvas.name}" ({canvas.width}x{canvas.height}).')


@canvas_app.command("delete")
def canvas_delete(
    ctx: typer.Context,
    name: CanvasArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a canvas that no brand uses."""
    with _service(ctx) as service:
        canvas = service.canvases.find(name)
        if not yes and not typer.confirm(f'Delete "{canvas.name}"?', err=True):
            raise typer.Exit(code=1)
        service.canvases.delete(canvas.id)
    _say(get_state(ctx), f'Deleted "{canvas.name}".')


@canvas_app.command("export")
def canvas_export(ctx: typer.Context, name: CanvasArgument, file: OutputOption = None) -> None:
    """Export a canvas as JSON (to a file, or to the screen)."""
    with _service(ctx) as service:
        payload = service.canvases.export_canvas(service.canvases.find(name).id)
    _write_payload(ctx, payload, file)


@canvas_app.command("import")
def canvas_import(
    ctx: typer.Context,
    file: InputFile,
    name: Annotated[str | None, typer.Option(help="Name for the new canvas.")] = None,
) -> None:
    """Import a canvas from a JSON file made by `canvas export`."""
    payload = _read_payload(file, "canvas")
    with _service(ctx) as service:
        canvas = service.canvases.import_canvas(payload, name=name)
    _say(get_state(ctx), f'Imported "{canvas.name}" ({canvas.width}x{canvas.height}).')


def _palette_table(palette: Palette) -> Table:
    table = _group(palette.name, "Color", "Light", "Dark")
    for name, pair in palette.colors.model_dump().items():
        table.add_row(name, _swatch(pair["light"]), _swatch(pair["dark"]))
    return table


@palette_app.command("list")
def palette_list(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List palettes: the built-in ones first, then yours."""
    with _service(ctx) as service:
        palettes = service.palettes.list_palettes()
    if json_output:
        _show_json([p.model_dump(mode="json") for p in palettes])
        return
    table = Table(title="Palettes")
    for column in ("Name", "Type", "Primary", "Secondary", "Id"):
        table.add_column(column)
    for p in palettes:
        table.add_row(
            p.name,
            p.type,
            _swatch(p.colors.primary.light),
            _swatch(p.colors.secondary.light),
            p.id,
        )
    output.console.print(table)


@palette_app.command("show")
def palette_show(
    ctx: typer.Context, name: PaletteArgument, json_output: JsonOption = False
) -> None:
    """Show every color of a palette."""
    with _service(ctx) as service:
        palette = service.palettes.find(name)
    if json_output:
        _show_json(palette.model_dump(mode="json"))
    else:
        output.console.print(_palette_table(palette))


@palette_app.command("add")
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
    with _service(ctx) as service:
        if from_brand:
            colors = service.find(from_brand).data.colors
        else:
            colors = service.palettes.find(from_palette or "midnight").colors
        palette = service.palettes.create(name, colors)
    _say(get_state(ctx), f'Created "{palette.name}".')


@palette_app.command("set")
def palette_set(
    ctx: typer.Context,
    name: PaletteArgument,
    path: Annotated[str, typer.Argument(help="Color, such as primary.light or text_alt.dark.")],
    value: Annotated[str, typer.Argument(help="New color, like #2563eb.")],
) -> None:
    """Change one color of a palette of your own."""
    with _service(ctx) as service:
        service.palettes.set_color(service.palettes.find(name).id, path, value)
    _say(get_state(ctx), f"{path} = {value}")


@palette_app.command("rename")
def palette_rename(ctx: typer.Context, name: PaletteArgument, new_name: str) -> None:
    """Rename a palette of your own."""
    with _service(ctx) as service:
        current = service.palettes.find(name)
        if current.name == new_name.strip():
            output.error(f'The palette is already named "{current.name}".')
            raise typer.Exit(code=1)
        palette = service.palettes.update(current.id, name=new_name)
    _say(get_state(ctx), f'Renamed to "{palette.name}".')


@palette_app.command("duplicate")
def palette_duplicate(ctx: typer.Context, name: PaletteArgument, new_name: str) -> None:
    """Copy a palette, built in or not, as a palette of your own."""
    with _service(ctx) as service:
        palette = service.palettes.duplicate(service.palettes.find(name).id, new_name)
    _say(get_state(ctx), f'Created "{palette.name}".')


@palette_app.command("delete")
def palette_delete(
    ctx: typer.Context,
    name: PaletteArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a palette of your own. Brands made from it keep their colors."""
    with _service(ctx) as service:
        palette = service.palettes.find(name)
        if not yes and not typer.confirm(f'Delete "{palette.name}"?', err=True):
            raise typer.Exit(code=1)
        service.palettes.delete(palette.id)
    _say(get_state(ctx), f'Deleted "{palette.name}".')


@palette_app.command("export")
def palette_export(ctx: typer.Context, name: PaletteArgument, file: OutputOption = None) -> None:
    """Export a palette as JSON (to a file, or to the screen)."""
    with _service(ctx) as service:
        payload = service.palettes.export_palette(service.palettes.find(name).id)
    _write_payload(ctx, payload, file)


@palette_app.command("import")
def palette_import(
    ctx: typer.Context,
    file: InputFile,
    name: Annotated[str | None, typer.Option(help="Name for the new palette.")] = None,
) -> None:
    """Import a palette from a JSON file made by `palette export`."""
    payload = _read_payload(file, "palette")
    with _service(ctx) as service:
        palette = service.palettes.import_palette(payload, name=name)
    _say(get_state(ctx), f'Imported "{palette.name}".')


def _layout_table(layout: Layout, canvas: Canvas) -> Table:
    table = _group(layout.name)
    table.add_row("id", layout.id)
    table.add_row("type", layout.type)
    table.add_row("canvas", f"{_size(canvas)}  [{canvas.id}]")
    for name, value in _layout_settings(layout).items():
        table.add_row(name, str(value))
    table.add_row("used by", ", ".join(layout.used_by))
    return table


@layout_app.command("list")
def layout_list(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """List layouts: the built-in ones first, then yours."""
    with _service(ctx) as service:
        layouts = service.layouts.list_layouts()
        canvases = {c.id: c for c in service.canvases.list_canvases()}
    if json_output:
        _show_json([lay.model_dump(mode="json") for lay in layouts])
        return
    table = Table(title="Layouts")
    for column in ("Name", "Type", "Canvas", "Slides", "Used by", "Id"):
        table.add_column(column)
    for lay in layouts:
        table.add_row(
            lay.name,
            lay.type,
            _size(canvases[lay.canvas_id]),
            str(lay.slides_count),
            ", ".join(lay.used_by),
            lay.id,
        )
    output.console.print(table)


@layout_app.command("show")
def layout_show(ctx: typer.Context, name: LayoutArgument, json_output: JsonOption = False) -> None:
    """Show every setting of a layout and the brands that use it."""
    with _service(ctx) as service:
        layout = service.layouts.find(name)
        canvas = service.canvases.get(layout.canvas_id)
    if json_output:
        _show_json(layout.model_dump(mode="json"))
    else:
        output.console.print(_layout_table(layout, canvas))


@layout_app.command("add")
def layout_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the new layout.")],
    from_layout: Annotated[
        str | None, typer.Option("--from-layout", help="Start from this layout (default: Default).")
    ] = None,
) -> None:
    """Create a layout from another layout. Change it afterwards with `layout set`."""
    with _service(ctx) as service:
        source = service.layouts.find(from_layout or "Default")
        layout = service.layouts.duplicate(source.id, name)
    _say(get_state(ctx), f'Created "{layout.name}".')


@layout_app.command("set")
def layout_set(
    ctx: typer.Context,
    name: LayoutArgument,
    path: Annotated[str, typer.Argument(help="Setting, such as margin_top or slides_count.")],
    value: Annotated[str, typer.Argument(help="New value. For canvas_id: a canvas name or id.")],
) -> None:
    """Change one setting of a layout of your own. Brands using it follow the change."""
    with _service(ctx) as service:
        service.layouts.change(service.layouts.find(name).id, path, value)
    _say(get_state(ctx), f"{path} = {value}")


@layout_app.command("settings")
def layout_settings(
    ctx: typer.Context, name: LayoutArgument, json_output: JsonOption = False
) -> None:
    """List the settings that `layout set` accepts, with their values."""
    with _service(ctx) as service:
        layout = service.layouts.find(name)
    values = {"canvas_id": layout.canvas_id, **_layout_settings(layout)}
    if json_output:
        _show_json(values)
        return
    table = Table(title="Layout settings")
    table.add_column("Setting")
    table.add_column("Value")
    for key, value in values.items():
        table.add_row(key, str(value))
    output.console.print(table)


@layout_app.command("rename")
def layout_rename(ctx: typer.Context, name: LayoutArgument, new_name: str) -> None:
    """Rename a layout of your own."""
    with _service(ctx) as service:
        current = service.layouts.find(name)
        if current.name == new_name.strip():
            output.error(f'The layout is already named "{current.name}".')
            raise typer.Exit(code=1)
        layout = service.layouts.update(current.id, name=new_name)
    _say(get_state(ctx), f'Renamed to "{layout.name}".')


@layout_app.command("duplicate")
def layout_duplicate(ctx: typer.Context, name: LayoutArgument, new_name: str) -> None:
    """Copy a layout, built in or not, as a layout of your own."""
    with _service(ctx) as service:
        layout = service.layouts.duplicate(service.layouts.find(name).id, new_name)
    _say(get_state(ctx), f'Created "{layout.name}".')


@layout_app.command("delete")
def layout_delete(
    ctx: typer.Context,
    name: LayoutArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a layout that no brand uses."""
    with _service(ctx) as service:
        layout = service.layouts.find(name)
        if not yes and not typer.confirm(f'Delete "{layout.name}"?', err=True):
            raise typer.Exit(code=1)
        service.layouts.delete(layout.id)
    _say(get_state(ctx), f'Deleted "{layout.name}".')


@layout_app.command("export")
def layout_export(ctx: typer.Context, name: LayoutArgument, file: OutputOption = None) -> None:
    """Export a layout, with its canvas, as JSON (to a file, or to the screen)."""
    with _service(ctx) as service:
        payload = service.layouts.export_layout(service.layouts.find(name).id)
    _write_payload(ctx, payload, file)


@layout_app.command("import")
def layout_import(
    ctx: typer.Context,
    file: InputFile,
    name: Annotated[str | None, typer.Option(help="Name for the new layout.")] = None,
) -> None:
    """Import a layout from a JSON file made by `layout export`."""
    payload = _read_payload(file, "layout")
    with _service(ctx) as service:
        layout = service.layouts.import_layout(payload, name=name)
    _say(get_state(ctx), f'Imported "{layout.name}".')
