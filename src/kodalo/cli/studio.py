"""``studio`` commands: start a post from a repository. They parse input and show output only."""

import dataclasses
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Annotated

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.ai import AiConnectionError, AiConnections, AiInvalidError, AiSecretError
from kodalo.core.github import GitHubConnectivity, GitHubSettings
from kodalo.core.repo import (
    Documentation,
    LocalDetails,
    Manifest,
    ReadmeAnalysis,
    ReadmeAssistant,
    ReadmeService,
    RepoAnalyzer,
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
) -> Iterator[tuple[GitHubSettings, RepoService, RepoAnalyzer, ReadmeService, ReadmeAssistant]]:
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
        )
        ai = AiConnections(database)
        analyzer = RepoAnalyzer(
            repos, ai, data_dir / "parsers", data_dir / "frameworks", data_dir / "tooling"
        )
        readme = ReadmeService(database, repos)
        yield (
            GitHubConnectivity(database).get(),
            repos,
            analyzer,
            readme,
            ReadmeAssistant(readme, ai),
        )
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


def _documentation_text(docs: Documentation) -> str:
    found = [
        *docs.readmes,
        docs.changelog,
        docs.contributing,
        docs.license_file,
        docs.code_of_conduct,
        docs.security,
        f"{docs.docs_dir}/" if docs.docs_dir else "",
    ]
    return ", ".join(name for name in found if name) or "-"


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
        ("Frameworks", ", ".join(f"{f.name} ({f.category})" for f in info.frameworks) or "-"),
        ("Tooling", ", ".join(f"{t.name} ({t.category})" for t in info.tooling) or "-"),
        ("Monorepo", ", ".join(info.monorepo_signals) if info.is_monorepo else "No"),
        ("Documentation", _documentation_text(info.documentation)),
        ("Not read", ", ".join(f"{s.path} ({s.reason})" for s in info.skipped) or "-"),
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
    with _open(ctx) as (settings, *_):
        source = validate_source(settings, value)
    if as_json:
        output.console.print_json(data=dataclasses.asdict(source))
    else:
        output.console.print(f"{source.name}: {source.value}")


def _approve(plan_lines: list[str], tokens: tuple[int, int], target: str, yes: bool) -> bool:
    """Show what would be sent and what it costs, and ask. ``yes`` skips the question."""
    output.err_console.print(
        f"Send {' and '.join(plan_lines)} to {target}: about {tokens[0]} tokens in, "
        f"at most {tokens[1]} out."
    )
    if not yes and not typer.confirm("Continue?", err=True):
        output.err_console.print("Nothing was sent.")
        return False
    return True


def _refresh_with_ai(
    analyzer: RepoAnalyzer,
    settings: GitHubSettings,
    repo_id: str,
    yes: bool,
    reread: Callable[[], RepoInfo],
) -> RepoInfo | None:
    """Plan, confirm once and run the one AI analysis. Return the repository read again, if any."""
    plan = analyzer.plan(settings, repo_id)
    if not plan.files and not plan.dependencies and not plan.tool_files:
        output.err_console.print("Everything is already understood; nothing to ask.")
        return None
    lines: list[str] = []
    if plan.files:
        lines.append(f"the start of {', '.join(plan.files)}")
    if plan.dependencies or plan.tool_files:
        names = dict.fromkeys((*plan.names, *plan.tool_files))
        lines.append(
            f"package names ({', '.join(plan.dependencies) or 'none'}) and file names "
            f"({', '.join(names)})"
        )
    tokens = (plan.input_tokens, plan.max_output_tokens)
    if not _approve(lines, tokens, f"{plan.label} ({plan.model})", yes):
        return None
    result = analyzer.apply(settings, repo_id)
    saved = (*result.parsers, *result.frameworks, *result.tools)
    output.err_console.print(
        f"Saved {len(result.parsers)} parser config(s), {len(result.frameworks)} framework(s) and "
        f"{len(result.tools)} tool(s); used {result.input_tokens} tokens in, "
        f"{result.output_tokens} out."
    )
    for line in result.skipped:
        output.err_console.print(f"[yellow]{line}[/yellow]")
    return reread() if saved else None


def _ask_ai(
    assistant: ReadmeAssistant,
    readmes: ReadmeService,
    settings: GitHubSettings,
    repo_id: str,
    yes: bool,
) -> ReadmeAnalysis | None:
    """Plan, confirm once and run the one AI request. Return the analysis it improved."""
    plan = assistant.plan(repo_id)
    if not plan.documents:
        output.err_console.print("No document was read, so there is nothing to send.")
        return None
    lines = [f"the text of {', '.join(plan.documents)} (secret-looking lines removed)"]
    if not _approve(lines, (plan.input_tokens, plan.max_output_tokens), plan.label, yes):
        return None
    result = assistant.apply(settings, repo_id)
    output.err_console.print(
        f"Saved {result.installation} installation method(s), {result.capabilities} "
        f"capabilities, {result.features} feature(s) and {result.use_cases} use case(s); used "
        f"{result.input_tokens} tokens in, {result.output_tokens} out."
    )
    for line in result.skipped:
        output.err_console.print(f"[yellow]{line}[/yellow]")
    return readmes.get(repo_id)


def _show_readme(info: RepoInfo, analysis: ReadmeAnalysis, as_json: bool) -> None:
    if as_json:
        data = dataclasses.asdict(info)
        del data["paths"]  # only used while reading
        output.console.print_json(data={"repository": data, "readme": dataclasses.asdict(analysis)})
        return
    _show(info, False)
    purpose = Table(show_header=False, title="Purpose")
    purpose.add_row("Tagline", analysis.tagline or "-")
    purpose.add_row("Summary", analysis.summary or "-")
    output.console.print(purpose)
    for title, headers, rows in (
        (
            "Installation",
            ("Method", "Command", "Found in"),
            [(i.method, i.command or "-", i.evidence.file or "-") for i in analysis.installation],
        ),
        (
            "Capabilities",
            ("Capability", "Description", "Note", "Found in"),
            [
                (c.name, c.description or "-", c.note or "-", c.evidence.file or "-")
                for c in analysis.capabilities
            ],
        ),
        (
            "Features",
            ("Feature", "Description", "Based on"),
            [(f.name, f.description or "-", f.evidence.quote or "-") for f in analysis.features],
        ),
        (
            "Use cases",
            ("Use case", "Description", "Based on"),
            [(u.title, u.description or "-", u.evidence.quote or "-") for u in analysis.use_cases],
        ),
        (
            "Documents",
            ("Document", "Status", "Reason"),
            [(d.path, d.status, d.reason or "-") for d in analysis.documents],
        ),
    ):
        table = Table(*headers, title=title)
        for row in rows:
            table.add_row(*row)
        output.console.print(table)
    for warning in analysis.warnings:
        output.err_console.print(f"[yellow]{warning}[/yellow]")


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
            help="Ask the default AI model to read unknown project files and find frameworks.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="With an AI option: do not ask before sending."),
    ] = False,
    readme: Annotated[
        bool,
        typer.Option(
            "--readme",
            help="Also read the README and the docs it links to: purpose, installation, "
            "capabilities. Without AI. Kept; --refresh reads it again.",
        ),
    ] = False,
    readme_with_ai: Annotated[
        bool,
        typer.Option(
            "--readme-with-ai",
            help="Ask the default AI model to read those documents and write the purpose, "
            "installation, capabilities and use cases (implies --readme).",
        ),
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
    analysis: ReadmeAnalysis | None = None
    with _open(ctx) as (settings, repos, analyzer, readmes, assistant):
        source = validate_source(settings, value)
        info = repos.read(settings, source, details if supplied else None, refresh=refresh)
        if refresh_with_ai:
            info = (
                _refresh_with_ai(
                    analyzer,
                    settings,
                    info.id,
                    yes,
                    lambda: repos.read(
                        settings, source, details if supplied else None, refresh=True
                    ),
                )
                or info
            )
        if readme or readme_with_ai:
            analysis = readmes.read(settings, info.id, refresh=refresh)
            if readme_with_ai:
                analysis = _ask_ai(assistant, readmes, settings, info.id, yes) or analysis
    if analysis is None:
        _show(info, as_json)
        return
    _show_readme(info, analysis, as_json)


@app.command("list")
def list_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """List the repositories that were read before."""
    with _open(ctx) as (_, repos, *_):
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
    with _open(ctx) as (_, repos, *_):
        info = repos.get(repo_id)
    _show(info, as_json)
