"""Instagram routes: export the designed post to a folder, or post it to Instagram."""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from kodalo.api.routers.common import (
    COMMON,
    INVALID,
    NOT_FOUND,
    BrandsSvc,
    InstagramPost,
    RepoPath,
    Repos,
    studio_errors,
)
from kodalo.api.routers.studio.common import page_assets, post_choice
from kodalo.api.schemas import (
    ExportRequest,
    ExportResultResponse,
    PostRequest,
    PostResultResponse,
)
from kodalo.core.parsers.image.render import RenderError
from kodalo.core.settings.platforms import (
    PlatformConnectionError,
    PlatformInvalidError,
    PlatformSecretError,
)
from kodalo.core.tunnel import TunnelError

router = APIRouter(tags=["v1"])


POST_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_502_BAD_GATEWAY: {
        "description": "Instagram refused the post or could not be reached, or the public address "
        "for the pictures could not be set up."
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "The keychain or Microsoft Edge is not available."
    },
}


EXPORT_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Microsoft Edge is not available."},
}


@router.post(
    "/studio/repositories/{repo_id}/design/export",
    summary="Export the designed post to a folder",
    responses=COMMON | NOT_FOUND | INVALID | EXPORT_ERRORS,
)
def export_post(
    repo_id: RepoPath,
    body: ExportRequest,
    poster: InstagramPost,
    brands: BrandsSvc,
    repos: Repos,
) -> ExportResultResponse:
    """Make a picture of each slide and write them, with a caption.txt holding the caption,
    hashtags and alt text, into a new folder inside the chosen one, so the post can be posted by
    hand. Only for brands whose canvas is an Instagram one. Nothing is sent to Instagram."""
    with studio_errors():
        choice = post_choice(repo_id, body, brands)
        brand = brands.get(body.brand_id)
        try:
            exported = poster.export(
                choice, brand, page_assets(repos, brands, repo_id, brand), body.folder, body.mode
            )
        except RenderError as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    return ExportResultResponse(
        folder=str(exported.folder),
        pictures=[str(path) for path in exported.pictures],
        caption_file=str(exported.caption_file),
    )


@router.post(
    "/studio/repositories/{repo_id}/design/post",
    summary="Post the designed post to Instagram",
    responses=COMMON | NOT_FOUND | INVALID | POST_ERRORS,
)
def post_to_instagram(
    repo_id: RepoPath,
    body: PostRequest,
    poster: InstagramPost,
    brands: BrandsSvc,
    repos: Repos,
) -> PostResultResponse:
    """Make a picture of each slide, give the pictures a temporary public address with
    cloudflared (installing it first when it is missing), and post them with the caption, hashtags
    and alt text: one slide is a single image, more a carousel. Only for brands whose canvas is an
    Instagram one. It can take a minute or two."""
    with studio_errors():
        choice = post_choice(repo_id, body, brands)
        brand = brands.get(body.brand_id)
        try:
            posted = poster.post(
                choice, brand, page_assets(repos, brands, repo_id, brand), body.mode
            )
        except PlatformInvalidError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
        except (PlatformConnectionError, TunnelError) as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
        except (PlatformSecretError, RenderError) as error:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    return PostResultResponse(media_id=posted.media_id, permalink=posted.permalink)
