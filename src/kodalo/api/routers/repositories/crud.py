"""Add, list, check, get and remove repositories."""

from pathlib import Path as FsPath
from typing import Any

from fastapi import APIRouter, Response, status

from kodalo.api.routers.common import (
    COMMON,
    INVALID,
    STUDIO_ERRORS,
    GitHub,
    RepoPath,
    Repos,
    studio_errors,
)
from kodalo.api.schemas import (
    RepoReadRequest,
    RepoResponse,
    StudioSourceRequest,
    StudioSourceResponse,
)
from kodalo.core.repositories import suggest
from kodalo.core.studio import validate_source

router = APIRouter(tags=["v1"])

REPO_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No repository has that id."}
}


@router.get("/repositories", summary="List repositories", responses=COMMON)
def list_repositories(repos: Repos) -> list[RepoResponse]:
    """Return every added repository, sorted by owner and name."""
    return [RepoResponse.from_core(i) for i in repos.list_repos()]


@router.post(
    "/repositories/check",
    summary="Check a repository address or folder",
    responses=COMMON | INVALID | STUDIO_ERRORS,
)
def check_repository(
    body: StudioSourceRequest, github: GitHub, repos: Repos
) -> StudioSourceResponse:
    """Check the source against the saved GitHub mode. Nothing is stored.

    For a local folder the answer also carries values read from git to prefill the details form.
    """
    with studio_errors():
        source = validate_source(github.get(), body.source)
        suggested = suggest(FsPath(source.value)) if source.kind == "local_folder" else None
        return StudioSourceResponse.from_core(source, repos.stored(source), suggested)


@router.post(
    "/repositories",
    summary="Add a repository",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | INVALID | STUDIO_ERRORS,
)
def add_repository(body: RepoReadRequest, github: GitHub, repos: Repos) -> RepoResponse:
    """Read the metadata, languages and structure of a repository and store them.

    A repository that was added before is returned from the database unless ``refresh`` is set.
    """
    with studio_errors():
        settings = github.get()
        source = validate_source(settings, body.source)
        details = body.details.to_core() if body.details else None
        info = repos.read(settings, source, details, refresh=body.refresh)
        return RepoResponse.from_core(info)


@router.get(
    "/repositories/{repo_id}",
    summary="Get a repository",
    responses=COMMON | REPO_NOT_FOUND,
)
def get_repository(repo_id: RepoPath, repos: Repos) -> RepoResponse:
    """Return one added repository."""
    with studio_errors():
        return RepoResponse.from_core(repos.get(repo_id))


@router.delete(
    "/repositories/{repo_id}",
    summary="Remove a repository",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON | REPO_NOT_FOUND,
)
def remove_repository(repo_id: RepoPath, repos: Repos) -> Response:
    """Remove a repository and everything saved about it (analysis, features, ideas)."""
    with studio_errors():
        repos.remove(repo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
