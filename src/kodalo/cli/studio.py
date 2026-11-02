"""``studio`` commands: start a post from a repository. They parse input and show output only."""

import dataclasses
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.github import GitHubConnectivity, GitHubSettings
from kodalo.core.repo import LocalDetails, RepoError, RepoInfo, RepoService
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir
from kodalo.core.studio import StudioInvalidError, validate_source

app = typer.Typer(
    help="Start a post from a repository.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]


@contextmanager
def _open(ctx: typer.Context) -> Iterator[tuple[GitHubSettings, RepoService]]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield GitHubConnectivity(database).get(), RepoService(database)
    except (StorageError, StudioInvalidError, RepoError) as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def _show(info: RepoInfo, as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=dataclasses.asdict(info))
        return
    table = Table(show_header=False, title=f"{info.owner}/{info.name}")
    for label, value in (
        ("URL", info.url),
        ("Description", info.description or "-"),
        ("Homepage", info.homepage or "-"),
        ("Default branch", info.default_branch or "-"),
        ("License", info.license or "-"),
        ("Topics", ", ".join(info.topics) or "-"),
        ("Private / fork / archived", f"{info.is_private} / {info.is_fork} / {info.is_archived}"),
        ("Last pushed", info.last_pushed_at or "-"),
        ("Files", str(info.file_count)),
        ("Read with", info.access_method),
        ("Top level", ", ".join(e.path + ("/" if e.type == "dir" else "") for e in info.top_level)),
    ):
        table.add_row(label, value)
    output.console.print(table)
    languages = Table("Language", "Bytes", "Percent")
    for language in info.languages:
        languages.add_row(language.name, str(language.bytes), f"{language.percent:.1f}")
    output.console.print(languages)
    for warning in info.warnings:
        output.err_console.print(f"[yellow]{warning}[/yellow]")


@app.command("source")
def source_command(
    ctx: typer.Context,
    value: Annotated[
        str, typer.Argument(help="A folder (local_folder mode) or a GitHub repository address.")
    ],
    as_json: JsonOption = False,
) -> None:
    """Check a repository against the GitHub mode. Exits with 1 when it is not valid."""
    with _open(ctx) as (settings, _):
        source = validate_source(settings, value)
    if as_json:
        output.console.print_json(data=dataclasses.asdict(source))
    else:
        output.console.print(f"{source.name}: {source.value}")


@app.command("read")
def read_command(
    ctx: typer.Context,
    value: Annotated[
        str, typer.Argument(help="A folder (local_folder mode) or a GitHub repository address.")
    ],
    refresh: Annotated[bool, typer.Option("--refresh", help="Read again, even if stored.")] = False,
    owner: Annotated[str, typer.Option(help="Local folder: the owner (required once).")] = "",
    repo: Annotated[str, typer.Option(help="Local folder: the repository name.")] = "",
    license_name: Annotated[
        str, typer.Option("--license", help="Local folder: the license, e.g. MIT.")
    ] = "",
    branch: Annotated[str, typer.Option(help="Local folder: the default branch.")] = "",
    description: Annotated[str, typer.Option(help="Local folder: a short description.")] = "",
    homepage: Annotated[str, typer.Option(help="Local folder: the home page address.")] = "",
    topic: Annotated[
        list[str] | None, typer.Option(help="Local folder: a topic; repeatable.")
    ] = None,
    private: Annotated[
        bool, typer.Option("--private", help="Local folder: it is private.")
    ] = False,
    fork: Annotated[bool, typer.Option("--fork", help="Local folder: it is a fork.")] = False,
    archived: Annotated[
        bool, typer.Option("--archived", help="Local folder: it is archived.")
    ] = False,
    as_json: JsonOption = False,
) -> None:
    """Read a repository's metadata, languages and structure, and store it."""
    details = LocalDetails(
        owner=owner,
        repo=repo,
        license=license_name,
        default_branch=branch,
        description=description,
        homepage=homepage,
        topics=tuple(topic or ()),
        is_private=private,
        is_fork=fork,
        is_archived=archived,
    )
    supplied = details != LocalDetails()
    with _open(ctx) as (settings, repos):
        source = validate_source(settings, value)
        info = repos.read(settings, source, details if supplied else None, refresh=refresh)
    _show(info, as_json)


@app.command("list")
def list_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """List the repositories that were read before."""
    with _open(ctx) as (_, repos):
        items = repos.list_repos()
    if as_json:
        output.console.print_json(data=[dataclasses.asdict(i) for i in items])
        return
    if not items:
        output.console.print("No repositories yet. Read one with: kodalo studio read <repository>")
        return
    table = Table("Repository", "Branch", "License", "Last read")
    for item in items:
        table.add_row(
            f"{item.owner}/{item.name}",
            item.default_branch or "-",
            item.license or "-",
            item.last_scanned_at or "-",
        )
    output.console.print(table)


@app.command("show")
def show_command(
    ctx: typer.Context,
    repo_id: Annotated[str, typer.Argument(help="Id of a stored repository (see studio list).")],
    as_json: JsonOption = False,
) -> None:
    """Show a stored repository."""
    with _open(ctx) as (_, repos):
        info = repos.get(repo_id)
    _show(info, as_json)
