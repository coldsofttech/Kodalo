"""Shared objects handed to route handlers with ``Depends``."""

import threading
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status

from kodalo.core.ai import AiConnections
from kodalo.core.brands.brand import BrandService
from kodalo.core.repositories import (
    ReadmeAssistant,
    ReadmeService,
    RepoAnalyzer,
    RepoService,
)
from kodalo.core.settings.appearance import Appearance
from kodalo.core.settings.github import GitHubConnectivity
from kodalo.core.settings.platforms import Platforms
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir
from kodalo.core.studio.copy import CopyAssistant
from kodalo.core.studio.design import DesignAssistant
from kodalo.core.studio.ideas import IdeasAssistant

# The data folder is always the per-user default. Tests point it somewhere else with configure().
_data_dir: Path | None = None
# The window sends several requests at once on start. Without this lock each could open (and
# migrate) the database at the same time, and the migrations would trip over one another.
_open_lock = threading.Lock()


@dataclass(frozen=True)
class Services:
    """What the process opens once: the database and the services on top of it."""

    database: Database
    brands: BrandService
    github: GitHubConnectivity
    repos: RepoService
    appearance: Appearance
    ai: AiConnections
    analyzer: RepoAnalyzer
    readme: ReadmeService
    assistant: ReadmeAssistant
    ideas: IdeasAssistant
    copy: CopyAssistant
    platforms: Platforms
    design: DesignAssistant


def data_dir() -> Path:
    """Return the folder holding the database and logo files."""
    return _data_dir or default_data_dir()


@lru_cache
def _build_services() -> Services:
    folder = data_dir()
    database = Database.open(database_path(folder))
    repos = RepoService(
        database,
        parsers_dir=folder / "parsers",
        frameworks_dir=folder / "frameworks",
        tooling_dir=folder / "tooling",
        previews_dir=folder / "social_previews",
        icons_dir=folder / "repo_icons",
    )
    ai = AiConnections(database)
    with suppress(Exception):  # old history is removed when the services start
        ai.history.purge_expired()
    readme = ReadmeService(database, repos)
    ideas = IdeasAssistant(readme, ai, database)
    platforms = Platforms(database)
    copy = CopyAssistant(readme, repos, ideas, ai, platforms, database)
    return Services(
        database,
        BrandService(database, folder),
        GitHubConnectivity(database),
        repos,
        Appearance(database),
        ai,
        RepoAnalyzer(repos, ai, folder / "parsers", folder / "frameworks", folder / "tooling"),
        readme,
        ReadmeAssistant(readme, ai),
        ideas,
        copy,
        platforms,
        DesignAssistant(copy, repos, platforms, ai, database),
    )


def _services() -> Services:
    with _open_lock:
        return _build_services()


def get_brand_service() -> BrandService:
    """Return the brand service, opening (and if needed migrating) the database on first use."""
    try:
        return _services().brands
    except StorageError as error:
        # Storage messages are written for users and never contain internals.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_github_connectivity() -> GitHubConnectivity:
    """Return the GitHub connectivity setting, opening the database on first use."""
    try:
        return _services().github
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_design_assistant() -> DesignAssistant:
    """Return the AI post design assistant, opening the database on first use."""
    try:
        return _services().design
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_platforms() -> Platforms:
    """Return the platform settings, opening the database on first use."""
    try:
        return _services().platforms
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_appearance() -> Appearance:
    """Return the appearance setting, opening the database on first use."""
    try:
        return _services().appearance
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_ai_connections() -> AiConnections:
    """Return the AI connections, opening the database on first use."""
    try:
        return _services().ai
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_repo_service() -> RepoService:
    """Return the repository service, opening the database on first use."""
    try:
        return _services().repos
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_repo_analyzer() -> RepoAnalyzer:
    """Return the AI repository analyzer, opening the database on first use."""
    try:
        return _services().analyzer
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_readme_service() -> ReadmeService:
    """Return the README analysis service, opening the database on first use."""
    try:
        return _services().readme
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_readme_assistant() -> ReadmeAssistant:
    """Return the AI README assistant, opening the database on first use."""
    try:
        return _services().assistant
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def reset_services() -> None:
    """Close the database and forget it, so the next request opens it again."""
    with _open_lock:
        if _build_services.cache_info().currsize:
            _build_services().database.close()
        _build_services.cache_clear()


def configure(data_dir: Path | None) -> None:
    """Use another data folder (``None`` for the default). Meant for tests."""
    global _data_dir
    reset_services()
    _data_dir = data_dir


def get_copy_assistant() -> CopyAssistant:
    """Return the AI post copy assistant, opening the database on first use."""
    try:
        return _services().copy
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


def get_ideas_assistant() -> IdeasAssistant:
    """Return the AI post ideas assistant, opening the database on first use."""
    try:
        return _services().ideas
    except StorageError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
