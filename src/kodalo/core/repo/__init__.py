"""Repo Reader: read a repository's metadata, languages and structure, and keep it."""

from kodalo.core.repo.errors import (
    RepoDetailsError,
    RepoError,
    RepoNotFoundError,
    RepoReadError,
)
from kodalo.core.repo.local_reader import Suggestion, suggest
from kodalo.core.repo.models import Entry, Language, LocalDetails, RepoInfo
from kodalo.core.repo.service import RepoService

__all__ = [
    "Entry",
    "Language",
    "LocalDetails",
    "RepoDetailsError",
    "RepoError",
    "RepoInfo",
    "RepoNotFoundError",
    "RepoReadError",
    "RepoService",
    "Suggestion",
    "suggest",
]
