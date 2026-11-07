"""Options, arguments and helpers the repository commands share."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Annotated

import typer

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.ai import AiConnections
from kodalo.core.repositories import (
    ReadmeAssistant,
    ReadmeService,
    RepoAnalyzer,
    RepoError,
    RepoService,
)
from kodalo.core.settings.ai import AiConnectionError, AiInvalidError, AiSecretError
from kodalo.core.settings.github import GitHubConnectivity, GitHubSettings
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir
from kodalo.core.studio import StudioInvalidError

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]


@contextmanager
def open_services(
    ctx: typer.Context,
) -> Generator[tuple[GitHubSettings, RepoService, RepoAnalyzer, ReadmeService, ReadmeAssistant]]:
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


RepoArgument = Annotated[
    str, typer.Argument(help="Id of an added repository (see repositories list).")
]


def approve(plan_lines: list[str], tokens: tuple[int, int], target: str, yes: bool) -> bool:
    """Show what would be sent and what it costs, and ask. ``yes`` skips the question."""
    output.err_console.print(
        f"Send {' and '.join(plan_lines)} to {target}: about {tokens[0]} tokens in, "
        f"at most {tokens[1]} out."
    )
    if not yes and not typer.confirm("Continue?", err=True):
        output.err_console.print("Nothing was sent.")
        return False
    return True
