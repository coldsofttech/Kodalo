"""Repo Reader: read a repository's metadata, languages and structure, and keep it."""

from kodalo.core.repo.ai_analyzer import AnalyzerPlan, AnalyzerResult, RepoAnalyzer
from kodalo.core.repo.errors import (
    RepoDetailsError,
    RepoError,
    RepoNotFoundError,
    RepoReadError,
)
from kodalo.core.repo.local_reader import Suggestion, suggest
from kodalo.core.repo.models import (
    Documentation,
    Entry,
    Framework,
    Language,
    Layout,
    LocalDetails,
    Manifest,
    NotableDir,
    RepoInfo,
    SkippedFile,
)
from kodalo.core.repo.service import RepoService

__all__ = [
    "AnalyzerPlan",
    "AnalyzerResult",
    "Documentation",
    "Entry",
    "Framework",
    "Language",
    "Layout",
    "LocalDetails",
    "Manifest",
    "NotableDir",
    "RepoAnalyzer",
    "RepoDetailsError",
    "RepoError",
    "RepoInfo",
    "RepoNotFoundError",
    "RepoReadError",
    "RepoService",
    "SkippedFile",
    "Suggestion",
    "suggest",
]
