"""``studio design``: how each slide of a written post is laid out."""

import dataclasses
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.table import Table

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
    YesOption,
    approve,
    choose,
    open_services,
    page_assets,
    warn,
)
from kodalo.cli.studio.platforms.instagram import export as instagram_export
from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.studio.design import Design

app = typer.Typer(
    help="Plan, make and show the design of a written post, and export its slides.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
# Platform commands (``export``) are added to this group without a name of their own.
app.add_typer(instagram_export.app)

SlideOption = Annotated[int, typer.Option("--slide", min=0, max=11, help="The slide, from 0.")]
OutputOption = Annotated[
    Path | None, typer.Option("--output", "-o", dir_okay=False, help="Write to a file.")
]


def _show(design: Design, as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=dataclasses.asdict(design))
        return
    table = Table("#", "Template", "Align", "Media", "Accent", "Icon", "Layout", title="Design")
    for number, slide in enumerate(design.slides):
        table.add_row(
            str(number),
            slide.template,
            slide.align,
            slide.media,
            slide.accent or "-",
            slide.icon or "-",
            "AI-written" if slide.html else "template",
        )
    output.console.print(table)
    warn(design.warnings)


def _write(text: str, destination: Path | None) -> None:
    if destination is None:
        output.console.print(text, markup=False, highlight=False)
        return
    destination.write_text(text, "utf-8")
    output.err_console.print(f"Wrote {destination}.")


@app.command("plan")
def plan_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    as_json: JsonOption = False,
) -> None:
    """Say what the AI would be sent to design the saved copy. Nothing is sent."""
    with open_services(ctx) as services:
        choice, chosen = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        canvas = chosen.canvas
        plan = services.design.plan(choice, (canvas.width, canvas.height))
    if as_json:
        output.console.print_json(data=dataclasses.asdict(plan))
        return
    output.console.print(f"Would send {', '.join(plan.items)} to {plan.label} ({plan.model}).")
    output.console.print(
        f"About {plan.input_tokens} tokens in, at most {plan.max_output_tokens} out."
    )


@app.command("make")
def make_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    yes: YesOption = False,
    as_json: JsonOption = False,
) -> None:
    """Ask the default AI model how to lay out each slide of the saved copy. Replaces the
    design saved before."""
    with open_services(ctx) as services:
        choice, chosen = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        canvas = (chosen.canvas.width, chosen.canvas.height)
        plan = services.design.plan(choice, canvas)
        tokens = (plan.input_tokens, plan.max_output_tokens)
        if not approve(plan.items, f"{plan.label} ({plan.model})", tokens, yes):
            raise typer.Exit(code=1)
        design = services.design.generate(choice, canvas)
    output.err_console.print(f"Used {design.input_tokens} tokens in, {design.output_tokens} out.")
    _show(design, as_json)


@app.command("show")
def show_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    as_json: JsonOption = False,
) -> None:
    """Show the saved design. Exits with 1 when none was made yet."""
    with open_services(ctx) as services:
        choice, _ = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        saved = services.design.saved(choice)
        if saved is None:
            raise RepoNotFoundError("No design was made for this post yet.")
    _show(saved, as_json)


@app.command("slide")
def slide_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    slide: SlideOption = 0,
    mode: Annotated[
        Literal["light", "dark"], typer.Option(help="The brand's colors to use.")
    ] = "light",
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    destination: OutputOption = None,
) -> None:
    """Export one slide as a self-contained HTML page (to stdout without --output)."""
    with open_services(ctx) as services:
        choice, chosen = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        page = services.design.slide_page(
            choice, slide, chosen, mode, page_assets(services, repo_id, chosen)
        )
        if page is None:
            raise RepoNotFoundError("That slide has no saved design.")
    _write(page, destination)


@app.command("svg")
def svg_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    slide: SlideOption = 0,
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    destination: OutputOption = None,
) -> None:
    """Export the drawing the AI made for one slide as SVG (to stdout without --output)."""
    with open_services(ctx) as services:
        choice, _ = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        svg = services.design.svg(choice, slide)
        if svg is None:
            raise RepoNotFoundError("That slide has no drawing.")
    _write(svg, destination)
