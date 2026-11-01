"""``brand`` commands: manage brand profiles. They parse input and show output only."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table
from rich.text import Text

from kodalo.cli import output
from kodalo.cli.state import State, get_state
from kodalo.core.brand import (
    STARTER_PALETTES,
    Brand,
    BrandError,
    BrandService,
    ContrastResult,
    available_fonts,
    bundled_fonts,
    check_colors,
    get_palette,
    list_paths,
    set_value,
    starter_brand,
)
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

app = typer.Typer(
    help="Manage brand profiles: colors, fonts, logo and layout.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
logo_app = typer.Typer(help="Set or remove a profile's logo.", no_args_is_help=True)
app.add_typer(logo_app, name="logo", rich_help_panel="Change a profile")

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]
BrandArgument = Annotated[str, typer.Argument(help="Brand name or id.")]


@contextmanager
def _service(ctx: typer.Context) -> Iterator[BrandService]:
    """Open the database for one command, turning expected failures into exit code 1."""
    state = get_state(ctx)
    data_dir = state.data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield BrandService(database, data_dir)
    except (BrandError, StorageError) as error:
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
        _show_json([{"id": b.id, "name": b.name, "is_default": b.is_default} for b in brands])
        return
    if not brands:
        _say(get_state(ctx), "No brands yet. Create one with: brand create NAME")
        return
    table = Table(title="Brands")
    for column in ("Name", "Default", "Canvas", "Id"):
        table.add_column(column)
    for b in brands:
        canvas = b.data.layout.canvas
        table.add_row(
            b.name, "yes" if b.is_default else "", f"{canvas.width}x{canvas.height}", b.id
        )
    output.console.print(table)


def _show_brand(brand: Brand) -> None:
    table = Table(title=f"{brand.name}{' (default)' if brand.is_default else ''}")
    table.add_column("Setting")
    table.add_column("Value")
    data = brand.data
    for name, pair in data.colors.model_dump().items():
        table.add_row(f"colors.{name}", f"light {pair['light']}   dark {pair['dark']}")
    for name, font in data.fonts.model_dump().items():
        table.add_row(f"fonts.{name}", f"{font['family']} ({font['source']})")
    for name, value in data.logo.model_dump().items():
        table.add_row(f"logo.{name}", "" if value is None else str(value))
    layout = data.layout.model_dump()
    canvas = layout.pop("canvas")
    table.add_row("layout.canvas", f"{canvas['preset']} {canvas['width']}x{canvas['height']}")
    for name, value in layout.items():
        table.add_row(f"layout.{name}", str(value))
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
        str, typer.Option(help="Starter palette: midnight, paper or graphite.")
    ] = "midnight",
    make_default: Annotated[bool, typer.Option("--default", help="Make it the default.")] = False,
) -> None:
    """Create a profile from a starter palette."""
    if get_palette(palette) is None:
        output.error(f"Unknown palette: {palette}. See: brand palettes")
        raise typer.Exit(code=1)
    with _service(ctx) as service:
        brand = service.create(name, starter_brand(palette))
        if make_default:
            brand = service.set_default(brand.id)
    _say(get_state(ctx), f'Created "{brand.name}".')


@app.command(rich_help_panel="Profiles")
def rename(ctx: typer.Context, name: BrandArgument, new_name: str) -> None:
    """Rename a profile."""
    with _service(ctx) as service:
        brand = service.update(service.find(name).id, name=new_name)
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


@app.command("set", rich_help_panel="Change a profile")
def set_command(
    ctx: typer.Context,
    name: BrandArgument,
    path: Annotated[str, typer.Argument(help="Setting, such as colors.primary.light.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Change one setting. Run `brand settings NAME` to list the paths you can use."""
    with _service(ctx) as service:
        brand = service.find(name)
        data = set_value(brand.data, path, value)
        service.update(brand.id, data=data)
    _say(get_state(ctx), f"{path} = {value}")


@app.command("settings", rich_help_panel="Change a profile")
def settings_command(ctx: typer.Context, name: BrandArgument) -> None:
    """List the setting paths that `set` accepts."""
    with _service(ctx) as service:
        paths = list_paths(service.find(name).data)
    output.console.print("\n".join(paths), markup=False, highlight=False)


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
def palettes(json_output: JsonOption = False) -> None:
    """List the starter palettes."""
    if json_output:
        _show_json([{"key": p.key, "title": p.title} for p in STARTER_PALETTES])
        return
    table = Table(title="Starter palettes")
    table.add_column("Key")
    table.add_column("Title")
    for p in STARTER_PALETTES:
        table.add_row(p.key, p.title)
    output.console.print(table)


@app.command(rich_help_panel="Look up")
def fonts(
    system: Annotated[
        bool, typer.Option("--system/--bundled", help="Include installed fonts (default) or not.")
    ] = True,
    json_output: JsonOption = False,
) -> None:
    """List the fonts a profile can use."""
    items = available_fonts() if system else bundled_fonts()
    if json_output:
        _show_json(
            [{"family": f.family, "category": f.category, "source": f.source} for f in items]
        )
        return
    table = Table(title="Fonts")
    for column in ("Family", "Category", "Source"):
        table.add_column(column)
    for f in items:
        table.add_row(f.family, f.category if f.source == "bundled" else "", f.source)
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
    if file is None:
        _show_json(payload)
        return
    file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _say(get_state(ctx), f"Wrote {file}")


@app.command("import", rich_help_panel="Share")
def import_command(
    ctx: typer.Context,
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Exported JSON file.")],
    name: Annotated[str | None, typer.Option(help="Name for the new profile.")] = None,
) -> None:
    """Import a profile from a JSON file made by `export`."""
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        output.error("That file is not valid JSON.")
        raise typer.Exit(code=1) from None
    if not isinstance(payload, dict):
        output.error("That file is not a Kodalo brand file.")
        raise typer.Exit(code=1)
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
