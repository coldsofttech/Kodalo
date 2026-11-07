"""A repository's social preview and icon images."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from kodalo.api.routers.common import COMMON, RepoPath, Repos, studio_errors

router = APIRouter(tags=["v1"])


@router.get(
    "/repositories/{repo_id}/social-preview",
    summary="Get a repository's social preview image",
    response_class=FileResponse,
    responses=COMMON
    | {
        status.HTTP_200_OK: {
            "description": "The image (PNG or JPEG).",
            "content": {"image/png": {}, "image/jpeg": {}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "No repository has that id, or it has no image."
        },
    },
)
def get_social_preview(repo_id: RepoPath, repos: Repos) -> FileResponse:
    """Return the social preview the owner uploaded on GitHub, saved when the repository was read
    with the GitHub CLI. ``has_social_preview`` on the repository says whether there is one."""
    with studio_errors():
        repos.get(repo_id)
    found = repos.social_preview(repo_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This repository has no social preview.")
    path, media_type = found
    return FileResponse(path, media_type=media_type)


@router.get(
    "/repositories/{repo_id}/icon",
    summary="Get the repository's icon",
    responses={
        **COMMON,
        status.HTTP_200_OK: {
            "description": "The icon image.",
            "content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}, "image/svg+xml": {}},
        },
        status.HTTP_404_NOT_FOUND: {"description": "No repository has that id, or it has no icon."},
    },
)
def get_icon(repo_id: RepoPath, repos: Repos) -> FileResponse:
    """Return the icon the README analysis with AI found in the repository and kept.
    ``has_icon`` on the repository says whether there is one."""
    with studio_errors():
        repos.get(repo_id)
    found = repos.icon(repo_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This repository has no icon.")
    path, media_type = found
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        },
    )
