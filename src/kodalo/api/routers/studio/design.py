"""How each slide of a written post is laid out, and its slide pages and drawings."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response, status

from kodalo.api.routers.common import (
    AI_UNREACHABLE,
    COMMON,
    INVALID,
    NOT_FOUND,
    BrandsSvc,
    DesignAi,
    RepoPath,
    Repos,
    ai_errors,
    studio_errors,
)
from kodalo.api.routers.studio.common import post_choice, post_choice_and_canvas
from kodalo.api.schemas import CopyRequest, DesignPlanResponse, DesignResponse
from kodalo.core.brands.brand import Brand, BrandError, BrandService
from kodalo.core.repositories import RepoNotFoundError, RepoService
from kodalo.core.studio.design import PageAssets, load_image
from kodalo.core.studio.slide_html import MAX_IMAGE_BYTES

router = APIRouter(tags=["v1"])


@router.get(
    "/studio/repositories/{repo_id}/design",
    summary="Get the saved post design",
    responses=COMMON | NOT_FOUND | INVALID,
)
def get_design(
    repo_id: RepoPath,
    body: Annotated[CopyRequest, Query()],
    assistant: DesignAi,
    brands: BrandsSvc,
) -> DesignResponse:
    """Return the design saved for this post; 404 when none was made yet."""
    with studio_errors():
        saved = assistant.saved(post_choice(repo_id, body, brands))
        if saved is None:
            raise RepoNotFoundError("No design was made for this post yet.")
        return DesignResponse.from_core(saved)


@router.post(
    "/studio/repositories/{repo_id}/design/plan",
    summary="Plan the AI post design request",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_design(
    repo_id: RepoPath, body: CopyRequest, assistant: DesignAi, brands: BrandsSvc
) -> DesignPlanResponse:
    """Say what the AI would be sent to design the saved copy and estimate the tokens. Nothing is
    sent."""
    with studio_errors(), ai_errors():
        choice, canvas = post_choice_and_canvas(repo_id, body, brands)
        return DesignPlanResponse.from_design(assistant.plan(choice, canvas))


@router.post(
    "/studio/repositories/{repo_id}/design",
    summary="Design the post with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def make_design(
    repo_id: RepoPath, body: CopyRequest, assistant: DesignAi, brands: BrandsSvc
) -> DesignResponse:
    """Ask the default AI model once how to lay out each slide of the saved copy: template,
    alignment, picture, icon and drawing, from what Settings > Platforms allows. The text is never
    the AI's. The plan is saved for this post, replacing the one saved before."""
    with studio_errors(), ai_errors():
        choice, canvas = post_choice_and_canvas(repo_id, body, brands)
        return DesignResponse.from_core(assistant.generate(choice, canvas))


# A slide page embeds everything it shows, so it may load nothing at all.
SLIDE_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox; frame-ancestors 'self'"
)


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


def _page_assets(
    repos: RepoService, brands: BrandService, repo_id: str, brand: Brand
) -> PageAssets:
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


@router.get(
    "/studio/repositories/{repo_id}/design/slide",
    summary="Get one AI-written slide as a page",
    responses={
        **COMMON,
        **NOT_FOUND,
        **INVALID,
        status.HTTP_200_OK: {"description": "The slide page.", "content": {"text/html": {}}},
    },
)
def get_design_slide(
    repo_id: RepoPath,
    body: Annotated[CopyRequest, Query()],
    slide: Annotated[int, Query(ge=0, le=11, description="The slide, counted from 0.")],
    assistant: DesignAi,
    brands: BrandsSvc,
    repos: Repos,
    mode: Annotated[Literal["light", "dark"], Query(description="The brand's colors.")] = "light",
) -> Response:
    """Return the page of a slide the AI wrote as HTML and CSS: cleaned, with the brand's colors
    for the mode, the pictures and icons filled in, and a policy that lets it load nothing and run
    nothing. It is meant to be shown in a sandboxed frame."""
    with studio_errors():
        choice = post_choice(repo_id, body, brands)
        brand = brands.get(body.brand_id)
        page = assistant.slide_page(
            choice, slide, brand, mode, _page_assets(repos, brands, repo_id, brand)
        )
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That slide has no AI-written layout.")
    return Response(
        page,
        media_type="text/html",
        headers={
            "Content-Security-Policy": SLIDE_CSP,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "/studio/repositories/{repo_id}/design/svg",
    summary="Get the drawing of one slide",
    responses={
        **COMMON,
        **NOT_FOUND,
        **INVALID,
        status.HTTP_200_OK: {"description": "The cleaned SVG.", "content": {"image/svg+xml": {}}},
    },
)
def get_design_svg(
    repo_id: RepoPath,
    body: Annotated[CopyRequest, Query()],
    slide: Annotated[int, Query(ge=0, le=11, description="The slide, counted from 0.")],
    assistant: DesignAi,
    brands: BrandsSvc,
) -> Response:
    """Return the drawing the AI made for one slide, already cleaned: plain shapes only."""
    with studio_errors():
        svg = assistant.svg(post_choice(repo_id, body, brands), slide)
    if svg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That slide has no drawing.")
    return Response(
        svg,
        media_type="image/svg+xml",
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )
