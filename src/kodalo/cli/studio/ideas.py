"""``studio ideas``: a strategy, three angles and five post ideas for a repository."""

import dataclasses

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.studio.common import (
    JsonOption,
    KindOption,
    NameOption,
    PostTypeOption,
    RepoArgument,
    YesOption,
    approve,
    open_services,
    warn,
)
from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.studio.ideas import Ideas

app = typer.Typer(
    help="Plan, make and show the post ideas of a repository.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)


def _show(ideas: Ideas, as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=dataclasses.asdict(ideas))
        return
    strategy = Table(show_header=False, title=f"Strategy ({ideas.focus or ideas.post_type})")
    strategy.add_row("Objective", ideas.strategy.objective or "-")
    strategy.add_row("Audience", ideas.strategy.audience or "-")
    strategy.add_row("Positioning", ideas.strategy.positioning or "-")
    strategy.add_row("Pain points", "\n".join(ideas.strategy.pain_points) or "-")
    strategy.add_row("Pillars", "\n".join(f"{n}: {d}" for n, d in ideas.strategy.pillars) or "-")
    output.console.print(strategy)
    angles = Table("Angle", "Type", "Summary", "Hooks", title="Angles")
    for angle in ideas.angles:
        angles.add_row(
            f"{angle.id} {angle.name}",
            angle.type,
            angle.summary,
            "\n".join(f"{h.id}: {h.text}" for h in angle.hooks),
        )
    output.console.print(angles)
    posts = Table("Idea", "Angle", "Hook", "Format", "Title", "Objective", title="Post ideas")
    for idea in ideas.post_ideas:
        posts.add_row(
            idea.id, idea.angle_id, idea.hook_id, idea.format, idea.working_title, idea.objective
        )
    output.console.print(posts)
    if ideas.claims_to_avoid:
        avoid = Table("Claim", "Type", "Why not", title="Claims to avoid")
        for claim in ideas.claims_to_avoid:
            avoid.add_row(claim.text, claim.type, claim.reason)
        output.console.print(avoid)
    warn(ideas.warnings)


@app.command("plan")
def plan_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    as_json: JsonOption = False,
) -> None:
    """Say what the AI would be sent and what it costs. Nothing is sent."""
    with open_services(ctx) as services:
        plan = services.ideas.plan(repo_id, post_type, kind, name)
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
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    yes: YesOption = False,
    as_json: JsonOption = False,
) -> None:
    """Ask the default AI model for a strategy, three angles and five post ideas. Saved."""
    with open_services(ctx) as services:
        plan = services.ideas.plan(repo_id, post_type, kind, name)
        if not approve(
            plan.items,
            f"{plan.label} ({plan.model})",
            (plan.input_tokens, plan.max_output_tokens),
            yes,
        ):
            raise typer.Exit(code=1)
        ideas = services.ideas.generate(repo_id, post_type, kind, name)
    output.err_console.print(f"Used {ideas.input_tokens} tokens in, {ideas.output_tokens} out.")
    _show(ideas, as_json)


@app.command("show")
def show_command(
    ctx: typer.Context,
    repo_id: RepoArgument,
    post_type: PostTypeOption = "tool",
    kind: KindOption = "",
    name: NameOption = "",
    as_json: JsonOption = False,
) -> None:
    """Show the saved post ideas. Exits with 1 when none were made yet."""
    with open_services(ctx) as services:
        saved = services.ideas.saved(repo_id, post_type, kind, name)
        if saved is None:
            raise RepoNotFoundError("No post ideas were made for this yet.")
    _show(saved, as_json)
