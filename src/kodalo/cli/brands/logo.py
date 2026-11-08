"""``brand logo`` commands: set or remove a profile's logo."""

from pathlib import Path
from typing import Annotated

import typer

from kodalo.cli.brands.common import (
    BrandArgument,
    open_service,
    say,
)
from kodalo.cli.state import get_state

app = typer.Typer(help="Set or remove a profile's logo.", no_args_is_help=True)


@app.command("set")
def logo_set(
    ctx: typer.Context,
    name: BrandArgument,
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="PNG or SVG file.")],
    dark: Annotated[bool, typer.Option("--dark", help="Use it as the dark-mode logo.")] = False,
) -> None:
    """Set a profile's logo from a PNG or SVG file."""
    with open_service(ctx) as service:
        service.set_logo(service.find(name).id, file.read_bytes(), dark=dark)
    say(get_state(ctx), "Logo set.")


@app.command("remove")
def logo_remove(
    ctx: typer.Context,
    name: BrandArgument,
    dark: Annotated[bool, typer.Option("--dark", help="Remove the dark-mode logo.")] = False,
) -> None:
    """Remove a profile's logo."""
    with open_service(ctx) as service:
        service.remove_logo(service.find(name).id, dark=dark)
    say(get_state(ctx), "Logo removed.")
