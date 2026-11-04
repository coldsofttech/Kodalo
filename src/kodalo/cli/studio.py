"""``studio`` commands: start a post from a repository. They parse input and show output only."""

import dataclasses
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.ai import AiConnectionError, AiConnections, AiInvalidError, AiSecretError
from kodalo.core.github import GitHubConnectivity, GitHubSettings
from kodalo.core.repo import (
    LocalDetails,
    Manifest,
    ParserAssistant,
    RepoError,
    RepoInfo,
    RepoService,
)
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
def _open(
    ctx: typer.Context,
) -> Iterator[tuple[GitHubSettings, RepoService, ParserAssistant]]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        repos = RepoService(database, parsers_dir=data_dir / "parsers")
        assistant = ParserAssistant(repos, AiConnections(database), data_dir / "parsers")
        yield GitHubConnectivity(database).get(), repos, assistant
    except (
        StorageError,
        StudioInvalidError,
        RepoError,
        AiConnectionError,
        AiInvalidError,
        AiSecretError,
    ) as error:
        output.error(str(error))
        raise typer.Exit(code=1) from error
    finally:
        if database is not None:
            database.close()


def _manifest_text(manifest: Manifest) -> str:
    count = len(manifest.dependencies) + len(manifest.dev_dependencies)
    return f"{manifest.path} ({count} dependencies)" if count else manifest.path


def _show(info: RepoInfo, as_json: bool) -> None:
    if as_json:
        data = dataclasses.asdict(info)
        del data["paths"]  # only used while reading
        output.console.print_json(data=data)
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
        ("Notable folders", ", ".join(f"{d.path} ({d.purpose})" for d in info.notable_dirs) or "-"),
        (
            "Project files",
            ", ".join(_manifest_text(m) for m in info.manifests if not m.is_lockfile) or "-",
        ),
        ("Monorepo", ", ".join(info.monorepo_signals) if info.is_monorepo else "No"),
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
    with _open(ctx) as (settings, _, _a):
        source = validate_source(settings, value)
    if as_json:
        output.console.print_json(data=dataclasses.asdict(source))
    else:
        output.console.print(f"{source.name}: {source.value}")


def _write_parsers(
    assistant: ParserAssistant, settings: GitHubSettings, repo_id: str, yes: bool
) -> bool:
    """Plan, confirm and run the AI step. Return whether a parser config was saved."""
    plan = assistant.plan(settings, repo_id)
    if not plan.files:
        output.err_console.print("Every project file is already understood; nothing to ask.")
        return False
    output.err_console.print(
        f"Send {', '.join(plan.files)} to {plan.label} ({plan.model}): about "
        f"{plan.input_tokens} tokens in, at most {plan.max_output_tokens} out."
    )
    if not yes and not typer.confirm("Continue?", err=True):
        output.err_console.print("Nothing was sent.")
        return False
    result = assistant.apply(settings, repo_id)
    output.err_console.print(
        f"Saved {len(result.added)} parser config(s); used {result.input_tokens} tokens in, "
        f"{result.output_tokens} out."
    )
    for line in result.skipped:
        output.err_console.print(f"[yellow]{line}[/yellow]")
    return bool(result.added)


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
    refresh_with_ai: Annotated[
        bool,
        typer.Option(
            "--refresh-with-ai",
            help="Ask the default AI model to write parser configs for unknown project files.",
        ),
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="With --refresh-with-ai: do not ask before sending.")
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
    with _open(ctx) as (settings, repos, assistant):
        source = validate_source(settings, value)
        info = repos.read(settings, source, details if supplied else None, refresh=refresh)
        if refresh_with_ai and _write_parsers(assistant, settings, info.id, yes):
            info = repos.read(settings, source, details if supplied else None, refresh=True)
    _show(info, as_json)


@app.command("list")
def list_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """List the repositories that were read before."""
    with _open(ctx) as (_, repos, _a):
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
    with _open(ctx) as (_, repos, _a):
        info = repos.get(repo_id)
    _show(info, as_json)
