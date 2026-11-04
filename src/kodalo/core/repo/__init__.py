"""Repo Reader: read a repository's metadata, languages and structure, and keep it."""

from kodalo.core.repo.ai_parsers import ParserAssistant, ParserPlan, ParserResult
from kodalo.core.repo.errors import (
    RepoDetailsError,
    RepoError,
    RepoNotFoundError,
    RepoReadError,
)
from kodalo.core.repo.local_reader import Suggestion, suggest
from kodalo.core.repo.models import (
    Entry,
    Language,
    Layout,
    LocalDetails,
    Manifest,
    NotableDir,
    RepoInfo,
)
from kodalo.core.repo.service import RepoService

__all__ = [
    "Entry",
    "Language",
    "Layout",
    "LocalDetails",
    "Manifest",
    "NotableDir",
    "ParserAssistant",
    "ParserPlan",
    "ParserResult",
    "RepoDetailsError",
    "RepoError",
    "RepoInfo",
    "RepoNotFoundError",
    "RepoReadError",
    "RepoService",
    "Suggestion",
    "suggest",
]
