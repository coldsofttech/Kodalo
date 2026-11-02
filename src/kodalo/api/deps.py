"""Shared objects handed to route handlers with ``Depends``."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status

from kodalo.core.brand import BrandService
from kodalo.core.github import GitHubConnectivity
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

# The data folder is always the per-user default. Tests point it somewhere else with configure().
_data_dir: Path | None = None


@dataclass(frozen=True)
class Services:
    """What the process opens once: the database and the services on top of it."""

    database: Database
    brands: BrandService
    github: GitHubConnectivity


def data_dir() -> Path:
    """Return the folder holding the database and logo files."""
    return _data_dir or default_data_dir()


@lru_cache
def _services() -> Services:
    folder = data_dir()
    database = Database.open(database_path(folder))
    return Services(database, BrandService(database, folder), GitHubConnectivity(database))


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


def reset_services() -> None:
    """Close the database and forget it, so the next request opens it again."""
    if _services.cache_info().currsize:
        _services().database.close()
    _services.cache_clear()


def configure(data_dir: Path | None) -> None:
    """Use another data folder (``None`` for the default). Meant for tests."""
    global _data_dir
    reset_services()
    _data_dir = data_dir
