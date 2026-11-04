"""Shared objects handed to route handlers with ``Depends``."""

import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status

from kodalo.core.ai import AiConnections
from kodalo.core.appearance import Appearance
from kodalo.core.brand import BrandService
from kodalo.core.github import GitHubConnectivity
from kodalo.core.repo import ParserAssistant, RepoService
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

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
    parsers: ParserAssistant


def data_dir() -> Path:
    """Return the folder holding the database and logo files."""
    return _data_dir or default_data_dir()


@lru_cache
def _build_services() -> Services:
    folder = data_dir()
    database = Database.open(database_path(folder))
    repos = RepoService(database, parsers_dir=folder / "parsers")
    ai = AiConnections(database)
    return Services(
        database,
        BrandService(database, folder),
        GitHubConnectivity(database),
        repos,
        Appearance(database),
        ai,
        ParserAssistant(repos, ai, folder / "parsers"),
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


def get_parser_assistant() -> ParserAssistant:
    """Return the AI parser assistant, opening the database on first use."""
    try:
        return _services().parsers
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
