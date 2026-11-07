"""The strategy, angles and post ideas of a repository."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from kodalo.api.routers.common import (
    AI_UNREACHABLE,
    COMMON,
    INVALID,
    NOT_FOUND,
    IdeasAi,
    RepoPath,
    ai_errors,
    studio_errors,
)
from kodalo.api.schemas import IdeasPlanResponse, IdeasRequest, IdeasResponse
from kodalo.core.repositories import RepoNotFoundError

router = APIRouter(tags=["v1"])


@router.post(
    "/studio/repositories/{repo_id}/ideas/plan",
    summary="Plan the AI post ideas request",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_ideas(repo_id: RepoPath, body: IdeasRequest, assistant: IdeasAi) -> IdeasPlanResponse:
    """Say what the AI would be sent for the chosen post and estimate the tokens. Nothing is
    sent."""
    with studio_errors(), ai_errors():
        return IdeasPlanResponse.from_core(
            assistant.plan(repo_id, body.post_type, body.kind, body.name)
        )


@router.get(
    "/studio/repositories/{repo_id}/ideas",
    summary="Get the saved post ideas",
    responses=COMMON | NOT_FOUND,
)
def get_ideas(
    repo_id: RepoPath,
    assistant: IdeasAi,
    post_type: Annotated[Literal["tool", "feature"], Query(description="The kind of post.")],
    kind: Annotated[
        Literal["", "features", "use_cases", "capabilities"],
        Query(description="Which list the focus is in; empty for a tool post."),
    ] = "",
    name: Annotated[str, Query(max_length=128, description="The focus's name.")] = "",
) -> IdeasResponse:
    """Return the post ideas saved for this repository and focus; 404 when none were made yet."""
    with studio_errors():
        saved = assistant.saved(repo_id, post_type, kind, name)
        if saved is None:
            raise RepoNotFoundError("No post ideas were made for this yet.")
        return IdeasResponse.from_core(saved)


@router.post(
    "/studio/repositories/{repo_id}/ideas",
    summary="Plan post ideas with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def make_ideas(repo_id: RepoPath, body: IdeasRequest, assistant: IdeasAi) -> IdeasResponse:
    """Send the saved README analysis for the chosen tool, feature, use case or capability once
    to the default AI model and return a strategy, three angles with hooks and five post ideas.
    Claims are kept only when their quote was in what was sent. The result is saved for this
    repository and focus, replacing the ones saved before."""
    with studio_errors(), ai_errors():
        return IdeasResponse.from_core(
            assistant.generate(repo_id, body.post_type, body.kind, body.name)
        )
