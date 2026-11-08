"""``repositories add``: read a repository, and optionally its README, with or without the AI."""

from collections.abc import Callable
from typing import Annotated

import typer

from kodalo.cli import output
from kodalo.cli.repositories.common import JsonOption, approve, open_services
from kodalo.cli.repositories.show import show_readme, show_repo
from kodalo.core.repositories import (
    LocalDetails,
    ReadmeAnalysis,
    ReadmeAssistant,
    ReadmeService,
    RepoAnalyzer,
    RepoInfo,
)
from kodalo.core.settings.github import GitHubSettings
from kodalo.core.studio import validate_source


def run_ai_refresh(
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
    if not approve(lines, tokens, f"{plan.label} ({plan.model})", yes):
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


def ask_ai(
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
    if not approve(lines, (plan.input_tokens, plan.max_output_tokens), plan.label, yes):
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


def add_command(
    ctx: typer.Context,
    value: Annotated[
        str, typer.Argument(help="A folder (local_folder mode) or a GitHub repository address.")
    ],
    refresh: Annotated[bool, typer.Option("--refresh", help="Read again, even if added.")] = False,
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
    """Add a repository: read its metadata, languages and structure, and keep them."""
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
    with open_services(ctx) as (settings, repos, analyzer, readmes, assistant):
        source = validate_source(settings, value)
        info = repos.read(settings, source, details if supplied else None, refresh=refresh)
        if refresh_with_ai:
            info = (
                run_ai_refresh(
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
                analysis = ask_ai(assistant, readmes, settings, info.id, yes) or analysis
    if analysis is None:
        show_repo(info, as_json)
        return
    show_readme(info, analysis, as_json)
