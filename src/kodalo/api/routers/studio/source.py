"""Check a repository to start a post from."""

from pathlib import Path as FsPath

from fastapi import APIRouter

from kodalo.api.routers.common import COMMON, INVALID, GitHub, Repos, studio_errors
from kodalo.api.schemas import StudioSourceRequest, StudioSourceResponse
from kodalo.core.repositories import suggest
from kodalo.core.studio import validate_source

router = APIRouter(tags=["v1"])


@router.post(
    "/studio/source",
    summary="Check a repository to start a post from",
    responses=COMMON | INVALID,
)
def check_studio_source(
    body: StudioSourceRequest, github: GitHub, repos: Repos
) -> StudioSourceResponse:
    """Check the repository against the saved GitHub mode. Nothing is stored.

    For a local folder the answer also carries values read from git to prefill the details form.
    """
    with studio_errors():
        source = validate_source(github.get(), body.source)
        suggested = suggest(FsPath(source.value)) if source.kind == "local_folder" else None
        return StudioSourceResponse.from_core(source, repos.stored(source), suggested)
