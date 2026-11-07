"""``studio design export``: write a designed post to a folder, to post to Instagram by hand."""

from pathlib import Path
from typing import Annotated, Literal

import typer

from kodalo.cli import output
from kodalo.cli.studio.common import (
    BrandOption,
    HookOption,
    IdeaOption,
    JsonOption,
    KindOption,
    NameOption,
    PostTypeOption,
    RepoArgument,
    choose,
    open_services,
    page_assets,
)

app = typer.Typer(rich_markup_mode="rich", pretty_exceptions_enable=False)


@app.command("export")
def export_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    folder: Annotated[
        Path,
        typer.Option(
            "--folder", file_okay=False, help="An existing folder. The post goes into a new one."
        ),
    ],
    mode: Annotated[
        Literal["light", "dark"], typer.Option(help="The brand's colors to use.")
    ] = "light",
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    as_json: JsonOption = False,
) -> None:
    """Make a picture of every slide and write them, with a caption.txt, into a new folder inside
    --folder, to post by hand. Nothing is sent to Instagram. Needs Microsoft Edge."""
    with open_services(ctx) as services:
        choice, chosen = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        exported = services.poster.export(
            choice, chosen, page_assets(services, repo_id, chosen), str(folder), mode
        )
    if as_json:
        output.console.print_json(
            data={
                "folder": str(exported.folder),
                "pictures": [str(path) for path in exported.pictures],
                "caption_file": str(exported.caption_file),
            }
        )
        return
    output.console.print(f"Exported {len(exported.pictures)} picture(s) and caption.txt to:")
    output.console.print(str(exported.folder), markup=False, highlight=False)
