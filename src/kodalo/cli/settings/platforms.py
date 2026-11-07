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
    InstagramAccount,
    InstagramConnection,
    PlatformConnectionError,
    PlatformInvalidError,
    Platforms,
    PlatformSecretError,
    PlatformSettings,
)
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir
from kodalo.core.tunnel import TunnelError, TunnelManager

app = typer.Typer(
    help="Choose how many hashtags a post gets, and the ones every post carries.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

instagram_app = typer.Typer(
    help="Connect Kodalo to Instagram with an access token.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
app.add_typer(instagram_app, name="instagram")

tunnel_app = typer.Typer(
    help="Check or install cloudflared, the tool posting to Instagram needs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
instagram_app.add_typer(tunnel_app, name="tunnel")

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


@contextmanager
def _instagram(ctx: typer.Context) -> Generator[InstagramConnection]:
    """Open the database for one Instagram command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield InstagramConnection(database)
    except (PlatformInvalidError, PlatformConnectionError, PlatformSecretError, StorageError) as e:
        output.error(str(e))
        raise typer.Exit(code=1) from e
    finally:
        if database is not None:
            database.close()


def _show_account(account: InstagramAccount | None, as_json: bool) -> None:
    if as_json:
        output.console.print_json(
            data={
                "connected": account is not None,
                "username": account.username if account else "",
                "account_id": account.account_id if account else "",
                "account_type": account.account_type if account else "",
                "token_hint": account.token_hint if account else "",
                "connected_at": account.connected_at if account else "",
            }
        )
        return
    if account is None:
        output.console.print("Instagram is not connected.")
        return
    table = Table(show_header=False)
    table.add_row("Account", account.username)
    table.add_row("Account ID", account.account_id)
    table.add_row("Account type", account.account_type or "-")
    table.add_row("Token", f"...{account.token_hint}")
    table.add_row("Connected", account.connected_at)
    output.console.print(table)


@instagram_app.command("status")
def instagram_status_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Show the connected Instagram account. Does not contact Instagram."""
    with _instagram(ctx) as instagram:
        _show_account(instagram.get(), as_json)


@instagram_app.command("connect")
def instagram_connect_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Connect Instagram. The access token is asked for at a hidden prompt, or piped in, and
    never taken as an argument. It is checked with Meta and kept in the system keychain."""
    account_id = typer.prompt("Instagram account ID")
    token = typer.prompt("Access token", hide_input=True)
    with _instagram(ctx) as instagram:
        _show_account(instagram.connect(token, account_id), as_json)


@instagram_app.command("check")
def instagram_check_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Ask Instagram whether the saved token still works."""
    with _instagram(ctx) as instagram:
        _show_account(instagram.check(), as_json)


@tunnel_app.command("status")
def instagram_tunnel_status_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Show whether cloudflared, which posting needs, is installed. Installs nothing."""
    manager = TunnelManager(get_state(ctx).data_dir or default_data_dir())
    installed = manager.is_installed()
    if as_json:
        output.console.print_json(data={"installed": installed})
        return
    output.console.print(
        "cloudflared is installed." if installed else "cloudflared is not installed."
    )


@tunnel_app.command("install")
def instagram_tunnel_install_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """Install cloudflared (a third-party tool from Cloudflare) when it is missing."""
    manager = TunnelManager(get_state(ctx).data_dir or default_data_dir())
    try:
        manager.ensure_installed()
    except TunnelError as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    if as_json:
        output.console.print_json(data={"installed": True})
        return
    output.console.print("cloudflared is installed.")


@instagram_app.command("disconnect")
def instagram_disconnect_command(ctx: typer.Context) -> None:
    """Remove the token from the keychain and forget the account."""
    with _instagram(ctx) as instagram:
        instagram.disconnect()
        output.console.print("Instagram is disconnected.")
