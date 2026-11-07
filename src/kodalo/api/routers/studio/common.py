"""Helpers the copy and design routes share: which idea, for which brand, and the slide pictures."""

from kodalo.api.routers.common import BrandsSvc
from kodalo.api.schemas import CopyRequest
from kodalo.core.brands.brand import Brand, BrandError, BrandNotFoundError, BrandService
from kodalo.core.parsers.html.render import MAX_IMAGE_BYTES
from kodalo.core.repositories import RepoNotFoundError, RepoService
from kodalo.core.settings.platforms import PLATFORMS
from kodalo.core.studio import StudioInvalidError
from kodalo.core.studio.copy import Choice
from kodalo.core.studio.design import PageAssets, load_image


def post_choice_and_canvas(
    repo_id: str, body: CopyRequest, brands: BrandsSvc
) -> tuple[Choice, tuple[int, int]]:
    """The idea to write, the platform of the brand it is for (Instagram or a custom canvas) and
    the size of the brand's canvas."""
    try:
        canvas = brands.get(body.brand_id).canvas
    except BrandNotFoundError as error:
        raise RepoNotFoundError("That brand does not exist.") from error
    platform = canvas.platform_id
    if platform not in PLATFORMS:
        raise StudioInvalidError(
            f"Posts cannot be written for {platform} yet. Choose a brand whose canvas is for "
            f"one of: {', '.join(PLATFORMS)}."
        )
    choice = Choice(
        platform, repo_id, body.post_type, body.kind, body.name, body.idea_id, body.hook_id
    )
    return choice, (canvas.width, canvas.height)


def post_choice(repo_id: str, body: CopyRequest, brands: BrandsSvc) -> Choice:
    return post_choice_and_canvas(repo_id, body, brands)[0]


def _logo_file(brands: BrandService, name: str | None) -> tuple[str, bytes] | None:
    """The brand's logo file for a page, or ``None`` when there is none or it cannot be read."""
    if not name:
        return None
    try:
        data = brands.logos.read(name)
    except BrandError:
        return None
    if len(data) > MAX_IMAGE_BYTES:
        return None
    return ("image/png" if name.endswith(".png") else "image/svg+xml", data)


def page_assets(repos: RepoService, brands: BrandService, repo_id: str, brand: Brand) -> PageAssets:
    """Read the pictures and the logo a slide page embeds."""
    preview = repos.social_preview(repo_id)
    icon = repos.icon(repo_id)
    logo = brand.data.logo
    return PageAssets(
        load_image(*preview) if preview else None,
        load_image(*icon) if icon else None,
        _logo_file(brands, logo.file),
        _logo_file(brands, logo.dark_file),
    )
