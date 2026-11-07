"""The slides, caption and hashtags of a post idea."""

from typing import Annotated

from fastapi import APIRouter, Query

from kodalo.api.routers.common import (
    AI_UNREACHABLE,
    COMMON,
    INVALID,
    NOT_FOUND,
    BrandsSvc,
    CopyAi,
    RepoPath,
    ai_errors,
    studio_errors,
)
from kodalo.api.routers.studio.common import post_choice
from kodalo.api.schemas import CopyEdit, CopyPlanResponse, CopyRequest, PostCopyResponse
from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.studio.copy import Caption, Slide

router = APIRouter(tags=["v1"])


@router.get(
    "/studio/repositories/{repo_id}/copy",
    summary="Get the saved post copy",
    responses=COMMON | NOT_FOUND | INVALID,
)
def get_copy(
    repo_id: RepoPath,
    body: Annotated[CopyRequest, Query()],
    assistant: CopyAi,
    brands: BrandsSvc,
) -> PostCopyResponse:
    """Return the copy saved for this idea and hook; 404 when none was written yet."""
    with studio_errors():
        saved = assistant.saved(post_choice(repo_id, body, brands))
        if saved is None:
            raise RepoNotFoundError("No copy was written for this idea yet.")
        return PostCopyResponse.from_core(saved)


@router.post(
    "/studio/repositories/{repo_id}/copy/plan",
    summary="Plan the AI post copy request",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_copy(
    repo_id: RepoPath, body: CopyRequest, assistant: CopyAi, brands: BrandsSvc
) -> CopyPlanResponse:
    """Say what the AI would be sent for the chosen idea and estimate the tokens. Nothing is
    sent."""
    with studio_errors(), ai_errors():
        return CopyPlanResponse.from_core(assistant.plan(post_choice(repo_id, body, brands)))


@router.post(
    "/studio/repositories/{repo_id}/copy",
    summary="Write the post copy with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def make_copy(
    repo_id: RepoPath, body: CopyRequest, assistant: CopyAi, brands: BrandsSvc
) -> PostCopyResponse:
    """Send the chosen idea once to the default AI model and return the slide script or image
    text, a caption with an alternative opening, alt text and hashtags. The result is saved for
    this idea and hook, replacing the copy saved before."""
    with studio_errors(), ai_errors():
        return PostCopyResponse.from_core(assistant.generate(post_choice(repo_id, body, brands)))


@router.put(
    "/studio/repositories/{repo_id}/copy",
    summary="Save the edited post copy",
    responses=COMMON | NOT_FOUND | INVALID,
)
def save_copy(
    repo_id: RepoPath, body: CopyEdit, assistant: CopyAi, brands: BrandsSvc
) -> PostCopyResponse:
    """Replace the saved copy with the text as the user edited it; 404 when none was written."""
    with studio_errors():
        return PostCopyResponse.from_core(
            assistant.edit(
                post_choice(repo_id, body, brands),
                tuple(Slide(**slide.model_dump()) for slide in body.slides),
                Caption(body.caption.opening, tuple(body.caption.body), body.caption.cta),
                body.alt_opening,
                tuple(body.hashtags),
            )
        )
