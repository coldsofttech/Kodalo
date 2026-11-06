"""``brand`` commands: manage brand profiles. They parse input and show output only."""

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table
from rich.text import Text

from kodalo.cli import output
from kodalo.cli.brands import canvas, layout, logo, palette
from kodalo.cli.brands.common import (
    BrandArgument,
    JsonOption,
    group_table,
    layout_values,
    open_service,
    read_payload,
    say,
    show_json,
    size_text,
    swatch,
    write_payload,
)
from kodalo.cli.state import get_state
from kodalo.core.brands.brand import (
    Brand,
    ContrastResult,
    check_colors,
    list_paths,
    set_value,
)

app = typer.Typer(
    help="Manage brand profiles: colors, fonts, logo and layout.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
app.add_typer(logo.app, name="logo", rich_help_panel="Change a profile")
settings_app = typer.Typer(help="List and change the settings of a profile.", no_args_is_help=True)
app.add_typer(settings_app, name="settings", rich_help_panel="Change a profile")
app.add_typer(layout.app, name="layout", rich_help_panel="Layouts")
app.add_typer(palette.app, name="palette", rich_help_panel="Palettes")
app.add_typer(canvas.app, name="canvas", rich_help_panel="Canvases")


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
    with open_service(ctx) as service:
        brands = service.list_brands()
    if json_output:
        show_json(
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
        say(get_state(ctx), "No brands yet. Create one with: brand create NAME")
        return
    table = Table(title="Brands")
    for column in ("Name", "Default", "Layout", "Canvas", "Id"):
        table.add_column(column)
    for b in brands:
        table.add_row(
            b.name, "yes" if b.is_default else "", b.layout.name, size_text(b.canvas), b.id
        )
    output.console.print(table)


def _show_brand(brand: Brand) -> None:
    data = brand.data
    general = group_table(f"{brand.name}{' (default)' if brand.is_default else ''}")
    general.add_row("name", brand.name)
    general.add_row("default", "yes" if brand.is_default else "no")
    general.add_row("id", brand.id)
    general.add_row("created", brand.created_at)
    general.add_row("updated", brand.updated_at)
    colors = group_table("Colors", "Color", "Light", "Dark")
    for name, pair in data.colors.model_dump().items():
        colors.add_row(name, swatch(pair["light"]), swatch(pair["dark"]))
    fonts = group_table("Fonts", "Font", "Family", "Source")
    for name, font in data.fonts.model_dump().items():
        fonts.add_row(name, font["family"], font["source"])
    logo = group_table("Logo")
    for name, value in data.logo.model_dump().items():
        logo.add_row(name, "" if value is None else str(value))
    layout = group_table("Layout")
    layout.add_row("layout", f"{brand.layout.name}  [{brand.layout.id}]")
    layout.add_row("canvas", f"{size_text(brand.canvas)}  [{brand.canvas.id}]")
    for name, value in layout_values(brand.layout).items():
        layout.add_row(name, str(value))
    for table in (general, colors, fonts, logo, layout):
        output.console.print(table)


@app.command(rich_help_panel="Profiles")
def show(ctx: typer.Context, name: BrandArgument, json_output: JsonOption = False) -> None:
    """Show every setting of a profile."""
    with open_service(ctx) as service:
        brand = service.find(name)
    if json_output:
        show_json(brand.model_dump(mode="json"))
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
    with open_service(ctx) as service:
        brand = service.create(name, service.starter(palette))
        if make_default:
            brand = service.set_default(brand.id)
    say(get_state(ctx), f'Created "{brand.name}".')


@app.command(rich_help_panel="Profiles")
def rename(ctx: typer.Context, name: BrandArgument, new_name: str) -> None:
    """Rename a profile."""
    with open_service(ctx) as service:
        current = service.find(name)
        if current.name == new_name.strip():
            output.error(f'The brand is already named "{current.name}".')
            raise typer.Exit(code=1)
        brand = service.update(current.id, name=new_name)
    say(get_state(ctx), f'Renamed to "{brand.name}".')


@app.command(rich_help_panel="Profiles")
def delete(
    ctx: typer.Context,
    name: BrandArgument,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")] = False,
) -> None:
    """Delete a profile and its logo files."""
    with open_service(ctx) as service:
        brand = service.find(name)
        if not yes and not typer.confirm(f'Delete "{brand.name}"?', err=True):
            raise typer.Exit(code=1)
        service.delete(brand.id)
    say(get_state(ctx), f'Deleted "{brand.name}".')


@app.command("default", rich_help_panel="Profiles")
def default_command(ctx: typer.Context, name: BrandArgument) -> None:
    """Make a profile the default."""
    with open_service(ctx) as service:
        brand = service.set_default(service.find(name).id)
    say(get_state(ctx), f'"{brand.name}" is now the default.')


@app.command(rich_help_panel="Profiles")
def duplicate(ctx: typer.Context, name: BrandArgument, new_name: str) -> None:
    """Copy a profile, including its logo files."""
    with open_service(ctx) as service:
        brand = service.duplicate(service.find(name).id, new_name)
    say(get_state(ctx), f'Created "{brand.name}".')


@settings_app.command("set")
def settings_set(
    ctx: typer.Context,
    name: BrandArgument,
    path: Annotated[str, typer.Argument(help="Setting, such as colors.primary.light.")],
    value: Annotated[str, typer.Argument(help="New value.")],
) -> None:
    """Change one setting. Run `brand settings list NAME` to see the paths you can use."""
    with open_service(ctx) as service:
        brand = service.find(name)
        data = set_value(brand.data, path, value)
        service.update(brand.id, data=data)
    say(get_state(ctx), f"{path} = {value}")


@settings_app.command("list")
def settings_list(ctx: typer.Context, name: BrandArgument, json_output: JsonOption = False) -> None:
    """List the settings of a profile that `settings set` accepts, with their values."""
    with open_service(ctx) as service:
        data = service.find(name).data
    dumped = data.model_dump()
    values: dict[str, Any] = {}
    for path in list_paths(data):
        node: Any = dumped
        for part in path.split("."):
            node = node[part]
        values[path] = node
    if json_output:
        show_json(values)
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
    with open_service(ctx) as service:
        results = check_colors(service.find(name).data.colors)
    if json_output:
        show_json(
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
    with open_service(ctx) as service:
        items = service.fonts.list_fonts(system=system)
    if json_output:
        show_json([{"family": f.family, "category": f.category, "source": f.source} for f in items])
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
    with open_service(ctx) as service:
        payload = service.export_profile(service.find(name).id)
    write_payload(ctx, payload, file)


@app.command("import", rich_help_panel="Share")
def import_command(
    ctx: typer.Context,
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Exported JSON file.")],
    name: Annotated[str | None, typer.Option(help="Name for the new profile.")] = None,
) -> None:
    """Import a profile from a JSON file made by `export`."""
    payload = read_payload(file, "brand")
    with open_service(ctx) as service:
        brand = service.import_profile(payload, name=name)
    say(get_state(ctx), f'Imported "{brand.name}".')
