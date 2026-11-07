"""Read, analyze and describe the repositories that posts are made from."""

from fastapi import APIRouter

from kodalo.api.routers.common import (
    AI_UNREACHABLE,
    COMMON,
    INVALID,
    NOT_FOUND,
    STUDIO_ERRORS,
    Analyzer,
    GitHub,
    Readme,
    ReadmeAi,
    RepoPath,
    Repos,
    ai_errors,
    studio_errors,
)
from kodalo.api.schemas import (
    AnalysisPlanResponse,
    AnalysisResultResponse,
    ReadmePlanResponse,
    ReadmeReadRequest,
    ReadmeResponse,
    ReadmeResultResponse,
    RepoReadRequest,
    RepoResponse,
)
from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.studio import validate_source

router = APIRouter(tags=["v1"])


@router.post(
    "/studio/repositories",
    summary="Read a repository",
    responses=COMMON | INVALID | STUDIO_ERRORS,
)
def read_repository(body: RepoReadRequest, github: GitHub, repos: Repos) -> RepoResponse:
    """Read the metadata, languages and top-level structure, and store them.

    A repository that was read before is returned from the database unless ``refresh`` is set.
    """
    with studio_errors():
        settings = github.get()
        source = validate_source(settings, body.source)
        details = body.details.to_core() if body.details else None
        info = repos.read(settings, source, details, refresh=body.refresh)
        return RepoResponse.from_core(info)


@router.get("/studio/repositories", summary="List stored repositories", responses=COMMON)
def list_repositories(repos: Repos) -> list[RepoResponse]:
    """Return every repository that was read, sorted by owner and name."""
    return [RepoResponse.from_core(i) for i in repos.list_repos()]


@router.get(
    "/studio/repositories/{repo_id}",
    summary="Get a stored repository",
    responses=COMMON | NOT_FOUND,
)
def get_repository(repo_id: RepoPath, repos: Repos) -> RepoResponse:
    """Return one stored repository."""
    with studio_errors():
        return RepoResponse.from_core(repos.get(repo_id))


@router.post(
    "/studio/repositories/{repo_id}/analysis/plan",
    summary="Plan the AI analysis",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_analysis(repo_id: RepoPath, github: GitHub, analyzer: Analyzer) -> AnalysisPlanResponse:
    """List the project files, package names and file names the AI would be asked about and
    estimate the tokens. Nothing is sent."""
    with studio_errors(), ai_errors():
        return AnalysisPlanResponse.from_core(analyzer.plan(github.get(), repo_id))


@router.post(
    "/studio/repositories/{repo_id}/analysis",
    summary="Analyze a repository with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def run_analysis(repo_id: RepoPath, github: GitHub, analyzer: Analyzer) -> AnalysisResultResponse:
    """Ask the default AI model once for parser, framework and tooling configs, check each one,
    and save the valid ones. Read the repository again to use them."""
    with studio_errors(), ai_errors():
        return AnalysisResultResponse.from_core(analyzer.apply(github.get(), repo_id))


@router.post(
    "/studio/repositories/{repo_id}/readme",
    summary="Read the README and docs",
    responses=COMMON | NOT_FOUND | STUDIO_ERRORS,
)
def read_readme(
    repo_id: RepoPath, body: ReadmeReadRequest, github: GitHub, readme: Readme
) -> ReadmeResponse:
    """Read the README and the docs it links to (no AI) and keep what they say: purpose,
    installation methods and capabilities. A saved analysis is returned unless ``refresh`` is set.
    """
    with studio_errors():
        return ReadmeResponse.from_core(readme.read(github.get(), repo_id, refresh=body.refresh))


@router.get(
    "/studio/repositories/{repo_id}/readme",
    summary="Get the saved README analysis",
    responses=COMMON | NOT_FOUND,
)
def get_readme(repo_id: RepoPath, readme: Readme) -> ReadmeResponse:
    """Return the saved README analysis; 404 when the documents were not read yet."""
    with studio_errors():
        saved = readme.get(repo_id)
        if saved is None:
            raise RepoNotFoundError("The README analysis has not been read yet.")
        return ReadmeResponse.from_core(saved)


@router.post(
    "/studio/repositories/{repo_id}/readme/analysis/plan",
    summary="Plan the AI README analysis",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_readme_analysis(repo_id: RepoPath, assistant: ReadmeAi) -> ReadmePlanResponse:
    """List the documents the AI would be sent and estimate the tokens. Nothing is sent."""
    with studio_errors(), ai_errors():
        return ReadmePlanResponse.from_core(assistant.plan(repo_id))


@router.post(
    "/studio/repositories/{repo_id}/readme/analysis",
    summary="Read the documents with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def run_readme_analysis(
    repo_id: RepoPath, github: GitHub, assistant: ReadmeAi
) -> ReadmeResultResponse:
    """Send the documents once to the default AI model and save the purpose, installation
    methods, capabilities and use cases that have evidence in the documents."""
    with studio_errors(), ai_errors():
        return ReadmeResultResponse.from_core(assistant.apply(github.get(), repo_id))
