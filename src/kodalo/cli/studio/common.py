"""Options, arguments and helpers the studio commands share."""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, Literal

import typer

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.ai import AiConnections
from kodalo.core.brands.brand import Brand, BrandError, BrandService
from kodalo.core.repositories import ReadmeService, RepoError, RepoService
from kodalo.core.settings.ai import AiConnectionError, AiInvalidError, AiSecretError
from kodalo.core.settings.platforms import PLATFORMS, Platforms
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir
from kodalo.core.studio import StudioInvalidError
from kodalo.core.studio.copy import Choice, CopyAssistant
from kodalo.core.studio.design import DesignAssistant
from kodalo.core.studio.ideas import IdeasAssistant

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]
YesOption = Annotated[
    bool, typer.Option("--yes", "-y", help="Do not ask before sending to the AI.")
]
RepoArgument = Annotated[
    str, typer.Argument(help="Id of an added repository (see repositories list).")
]
PostTypeOption = Annotated[
    Literal["tool", "feature"],
    typer.Option("--type", "-t", help="The kind of post: about the whole tool or one feature."),
]
KindOption = Annotated[
    Literal["", "features", "use_cases", "capabilities"],
    typer.Option(help="Feature post: which list the focus is in."),
]
NameOption = Annotated[str, typer.Option(help="Feature post: the name of the focus.")]
BrandOption = Annotated[
    str, typer.Option("--brand", "-b", help="The brand (name or id) the post is for.")
]
IdeaOption = Annotated[str, typer.Option("--idea", help="The post idea, e.g. idea-1.")]
HookOption = Annotated[
    str, typer.Option("--hook", help="The hook to open with; the idea's own when left out.")
]


@dataclass(frozen=True)
class Services:
    """What one command opens: the services the studio steps are built on."""

    repos: RepoService
    brands: BrandService
    ideas: IdeasAssistant
    copy: CopyAssistant
    design: DesignAssistant


@contextmanager
def open_services(ctx: typer.Context) -> Generator[Services]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        repos = RepoService(
            database,
            parsers_dir=data_dir / "parsers",
            frameworks_dir=data_dir / "frameworks",
            tooling_dir=data_dir / "tooling",
            previews_dir=data_dir / "social_previews",
            icons_dir=data_dir / "repo_icons",
        )
        ai = AiConnections(database)
        readme = ReadmeService(database, repos)
        ideas = IdeasAssistant(readme, ai, database)
        platforms = Platforms(database)
        copy = CopyAssistant(readme, repos, ideas, ai, platforms, database)
        yield Services(
            repos,
            BrandService(database, data_dir),
            ideas,
            copy,
            DesignAssistant(copy, repos, platforms, ai, database),
        )
    except (
        StorageError,
        StudioInvalidError,
        RepoError,
        BrandError,
        AiConnectionError,
        AiInvalidError,
        AiSecretError,
    ) as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def choose(
    services: Services,
    repo_id: str,
    brand_ref: str,
    post_type: str,
    kind: str,
    name: str,
    idea_id: str,
    hook_id: str,
) -> tuple[Choice, Brand]:
    """The idea to write and the brand it is for (Instagram or a custom canvas)."""
    brand = services.brands.find(brand_ref)
    platform = brand.canvas.platform_id
    if platform not in PLATFORMS:
        raise StudioInvalidError(
            f"Posts cannot be written for {platform} yet. Choose a brand whose canvas is for "
            f"one of: {', '.join(PLATFORMS)}."
        )
    services.repos.get(repo_id)
    return Choice(platform, repo_id, post_type, kind, name, idea_id, hook_id), brand


def approve(items: tuple[str, ...], label: str, tokens: tuple[int, int], yes: bool) -> bool:
    """Show what would be sent and what it costs, and ask. ``yes`` skips the question."""
    output.err_console.print(
        f"Send {' and '.join(items)} to {label}: about {tokens[0]} tokens in, "
        f"at most {tokens[1]} out."
    )
    if not yes and not typer.confirm("Continue?", err=True):
        output.err_console.print("Nothing was sent.")
        return False
    return True


def warn(lines: tuple[str, ...]) -> None:
    for line in lines:
        output.err_console.print(f"[yellow]{line}[/yellow]")
