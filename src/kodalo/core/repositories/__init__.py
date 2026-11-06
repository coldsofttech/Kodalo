"""Repo Reader: read a repository's metadata, languages and structure, and keep it."""

from kodalo.core.repositories.ai.analyzer import AnalyzerPlan, AnalyzerResult, RepoAnalyzer
from kodalo.core.repositories.ai.readme import ReadmeAssistant, ReadmePlan, ReadmeResult
from kodalo.core.repositories.errors import (
    RepoDetailsError,
    RepoError,
    RepoNotFoundError,
    RepoReadError,
)
from kodalo.core.repositories.models import (
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
from kodalo.core.repositories.readers.local import Suggestion, suggest
from kodalo.core.repositories.readme import (
    Capability,
    ClaimFlag,
    Document,
    Evidence,
    Feature,
    Installation,
    ReadmeAnalysis,
    ReadmeService,
    UseCase,
)
from kodalo.core.repositories.service import RepoService

__all__ = [
    "AnalyzerPlan",
    "AnalyzerResult",
    "Capability",
    "ClaimFlag",
    "Document",
    "Documentation",
    "Entry",
    "Evidence",
    "Feature",
    "Framework",
    "Installation",
    "Language",
    "Layout",
    "LocalDetails",
    "Manifest",
    "NotableDir",
    "ReadmeAnalysis",
    "ReadmeAssistant",
    "ReadmePlan",
    "ReadmeResult",
    "ReadmeService",
    "RepoAnalyzer",
    "RepoDetailsError",
    "RepoError",
    "RepoInfo",
    "RepoNotFoundError",
    "RepoReadError",
    "RepoService",
    "SkippedFile",
    "Suggestion",
    "UseCase",
    "suggest",
]
