"""Helpers the copy and design routes share: which idea, for which brand."""

from kodalo.api.routers.common import BrandsSvc
from kodalo.api.schemas import CopyRequest
from kodalo.core.brands.brand import BrandNotFoundError
from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.studio import StudioInvalidError
from kodalo.core.studio.copy import Choice


def post_choice_and_canvas(
    repo_id: str, body: CopyRequest, brands: BrandsSvc
) -> tuple[Choice, tuple[int, int]]:
    """The idea to write, the platform of the brand it is for (only Instagram is supported so
    far) and the size of the brand's canvas."""
    try:
        canvas = brands.get(body.brand_id).canvas
    except BrandNotFoundError as error:
        raise RepoNotFoundError("That brand does not exist.") from error
    platform = canvas.platform_id
    if platform != "instagram":
        raise StudioInvalidError(
            "Posts can only be written for Instagram so far. Choose a brand whose canvas is for "
            "Instagram."
        )
    choice = Choice(
        platform, repo_id, body.post_type, body.kind, body.name, body.idea_id, body.hook_id
    )
    return choice, (canvas.width, canvas.height)


def post_choice(repo_id: str, body: CopyRequest, brands: BrandsSvc) -> Choice:
    return post_choice_and_canvas(repo_id, body, brands)[0]
