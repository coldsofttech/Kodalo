"""``studio copy``: the slide script, caption, alternative opening and hashtags of a post."""

import dataclasses
import json
from pathlib import Path
from typing import Annotated, Any

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
    warn,
)
from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.studio import StudioInvalidError
from kodalo.core.studio.copy import Caption, PostCopy, Slide

app = typer.Typer(
    help="Plan, write, show and edit the copy of a post idea.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)


def show_copy(post: PostCopy, as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=dataclasses.asdict(post))
        return
    slides = Table("#", "Role", "Headline", "Body", "Visual note", title=f"{post.format} copy")
    for number, slide in enumerate(post.slides, 1):
        slides.add_row(str(number), slide.role, slide.headline, slide.body, slide.visual_note)
    output.console.print(slides)
    caption = Table(show_header=False, title="Caption")
    caption.add_row("Opening", post.caption.opening)
    caption.add_row("Body", "\n".join(post.caption.body) or "-")
    caption.add_row("Call to action", post.caption.cta or "-")
    caption.add_row("Alternative opening", post.alt_opening.text or "-")
    caption.add_row("Hashtags", " ".join(post.hashtags) or "-")
    output.console.print(caption)
    if post.review_flags:
        flags = Table("Type", "Text", "Reason", title="Check before posting")
        for flag in post.review_flags:
            flags.add_row(flag.type, flag.text, flag.reason)
        output.console.print(flags)
    warn(post.warnings)


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
    """Say what the AI would be sent and what it costs. Nothing is sent."""
    with open_services(ctx) as services:
        choice, _ = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        plan = services.copy.plan(choice)
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
    """Ask the default AI model to write the copy of an idea. Replaces the copy saved before."""
    with open_services(ctx) as services:
        choice, _ = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        plan = services.copy.plan(choice)
        tokens = (plan.input_tokens, plan.max_output_tokens)
        if not approve(plan.items, f"{plan.label} ({plan.model})", tokens, yes):
            raise typer.Exit(code=1)
        post = services.copy.generate(choice)
    output.err_console.print(f"Used {post.input_tokens} tokens in, {post.output_tokens} out.")
    show_copy(post, as_json)


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
    """Show the saved copy. Exits with 1 when none was written yet."""
    with open_services(ctx) as services:
        choice, _ = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        saved = services.copy.saved(choice)
        if saved is None:
            raise RepoNotFoundError("No copy was written for this idea yet.")
    show_copy(saved, as_json)


def _read_edit(path: Path) -> tuple[tuple[Slide, ...], Caption, str, tuple[str, ...]]:
    """Read the text from a JSON file shaped like ``copy show --json``."""
    try:
        data: Any = json.loads(path.read_text("utf-8"))
        alt = data["alt_opening"]
        return (
            tuple(
                Slide(*(str(s[k]) for k in ("role", "headline", "body", "visual_note", "alt_text")))
                for s in data["slides"]
            ),
            Caption(
                str(data["caption"]["opening"]),
                tuple(str(line) for line in data["caption"]["body"]),
                str(data["caption"]["cta"]),
            ),
            str(alt["text"] if isinstance(alt, dict) else alt),
            tuple(str(tag) for tag in data["hashtags"]),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise StudioInvalidError(f"Cannot read the edited copy from {path}: {error}") from error


@app.command("edit")
def edit_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    brand: BrandOption,
    idea: IdeaOption,
    file: Annotated[
        Path,
        typer.Option(
            "--file", "-f", exists=True, dir_okay=False, help="JSON as from: copy show --json."
        ),
    ],
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    hook: HookOption = "",
    as_json: JsonOption = False,
) -> None:
    """Replace the saved copy with your edited text (slides, caption, alternative opening and
    hashtags); the limits are applied."""
    with open_services(ctx) as services:
        choice, _ = choose(services, repo_id, brand, post_type, kind, name, idea, hook)
        post = services.copy.edit(choice, *_read_edit(file))
    show_copy(post, as_json)
