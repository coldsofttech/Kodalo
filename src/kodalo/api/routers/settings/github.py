"""GitHub connectivity routes."""

from fastapi import APIRouter, HTTPException, status

from kodalo.api.routers.common import (
    COMMON,
    INVALID,
    GitHub,
)
from kodalo.api.schemas import (
    GitHubCheckResponse,
    GitHubSettingsResponse,
    GitHubSettingsUpdate,
)
from kodalo.core.settings.github import (
    GitHubInvalidError,
    check_connection,
)

router = APIRouter()


@router.get("/settings/github", summary="Get GitHub connectivity", responses=COMMON)
def get_github_settings(github: GitHub) -> GitHubSettingsResponse:
    """Return how Kodalo reaches GitHub. The default is the gh CLI."""
    return GitHubSettingsResponse.from_core(github.get())


@router.put("/settings/github", summary="Set GitHub connectivity", responses=COMMON | INVALID)
def set_github_settings(body: GitHubSettingsUpdate, github: GitHub) -> GitHubSettingsResponse:
    """Choose the way to reach GitHub: a local folder, the gh CLI or the web."""
    try:
        return GitHubSettingsResponse.from_core(
            github.save(
                body.mode,
                body.local_folder,
                body.manifest_limit,
                body.document_limit,
                body.document_max_kb,
            )
        )
    except GitHubInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/settings/github/check", summary="Check GitHub connectivity", responses=COMMON)
def check_github_settings(github: GitHub) -> GitHubCheckResponse:
    """Try the saved way of reaching GitHub once. A failure is reported in the body."""
    return GitHubCheckResponse.from_core(check_connection(github.get()))
