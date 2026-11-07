"""``platforms`` commands: how many hashtags a post gets and which ones every post carries. They
parse input and show output only."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.settings.platforms import (
    MAX_HASHTAGS,
    PLATFORMS,
    VISUALS,
    PlatformInvalidError,
    Platforms,
    PlatformSettings,
)
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

app = typer.Typer(
    help="Choose how many hashtags a post gets, and the ones every post carries.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]
PlatformArgument = Annotated[str, typer.Argument(help=f"One of: {', '.join(PLATFORMS)}.")]


@contextmanager
def _platforms(ctx: typer.Context) -> Generator[Platforms]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield Platforms(database)
    except (PlatformInvalidError, StorageError) as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def _show(settings: PlatformSettings, as_json: bool) -> None:
    if as_json:
        output.console.print_json(
            data={
                "platform": settings.platform,
                "hashtag_count": settings.hashtag_count,
                "default_hashtags": list(settings.default_hashtags),
                **{name: getattr(settings, name) for name in VISUALS},
            }
        )
        return
    table = Table(show_header=False)
    table.add_row("Platform", settings.platform)
    table.add_row("Hashtags per post", str(settings.hashtag_count))
    table.add_row("Default hashtags", " ".join(settings.default_hashtags) or "-")
    for name in VISUALS:
        table.add_row(
            name.replace("_", " ").capitalize(), "yes" if getattr(settings, name) else "no"
        )
    output.console.print(table)


def _pick(chosen: bool | None, current: bool) -> bool:
    return current if chosen is None else chosen


@app.command("show")
def show_command(
    ctx: typer.Context, platform: PlatformArgument, as_json: JsonOption = False
) -> None:
    """Show a platform's hashtag settings."""
    with _platforms(ctx) as platforms:
        _show(platforms.get(platform), as_json)


@app.command("set")
def set_command(
    ctx: typer.Context,
    platform: PlatformArgument,
    hashtags: Annotated[
        int | None,
        typer.Option(
            "--hashtags",
            help=f"Hashtags on each post, the default ones included, 0 to {MAX_HASHTAGS}.",
        ),
    ] = None,
    default_hashtags: Annotated[
        str | None,
        typer.Option(
            "--default-hashtags",
            help='Hashtags every post carries, separated by spaces, for example "#sweepito". '
            "Use an empty value to remove them.",
        ),
    ] = None,
    use_social_preview: Annotated[
        bool | None,
        typer.Option(
            "--use-social-preview/--no-social-preview",
            help="The designer may use the social preview.",
        ),
    ] = None,
    use_repo_icon: Annotated[
        bool | None,
        typer.Option(
            "--use-repo-icon/--no-repo-icon", help="The designer may use the repository icon."
        ),
    ] = None,
    use_icons: Annotated[
        bool | None, typer.Option("--use-icons/--no-icons", help="The designer may use icons.")
    ] = None,
    build_custom_images: Annotated[
        bool | None,
        typer.Option(
            "--build-custom-images/--no-custom-images",
            help="The designer may build custom images as needed.",
        ),
    ] = None,
    use_ai_templates: Annotated[
        bool | None,
        typer.Option(
            "--use-ai-templates/--no-ai-templates",
            help="The AI writes the HTML and CSS of each slide instead of the fixed templates.",
        ),
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Change a platform's settings. What you leave out stays as it is."""
    with _platforms(ctx) as platforms:
        current = platforms.get(platform)
        _show(
            platforms.save(
                platform,
                current.hashtag_count if hashtags is None else hashtags,
                current.default_hashtags if default_hashtags is None else default_hashtags,
                use_social_preview=_pick(use_social_preview, current.use_social_preview),
                use_repo_icon=_pick(use_repo_icon, current.use_repo_icon),
                use_icons=_pick(use_icons, current.use_icons),
                build_custom_images=_pick(build_custom_images, current.build_custom_images),
                use_ai_templates=_pick(use_ai_templates, current.use_ai_templates),
            ),
            as_json,
        )
