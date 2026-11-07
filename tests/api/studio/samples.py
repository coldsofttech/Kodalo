"""Core objects the Studio API and CLI tests hand back in place of the answers of the AI."""

from typing import Any, TypeVar

from kodalo.core.studio.copy import AltOpening, Caption, CopyPlan, PostCopy, Slide
from kodalo.core.studio.design import Design, DesignPlan, SlideDesign
from kodalo.core.studio.ideas import (
    Angle,
    AvoidedClaim,
    Claim,
    Hook,
    Ideas,
    IdeasPlan,
    PostIdea,
    Strategy,
)

T = TypeVar("T")

CLAIM = Claim("Tidies caches", "README.md", "tidy things")


def ideas() -> Ideas:
    return Ideas(
        post_type="tool",
        focus="",
        strategy=Strategy(
            "Awareness", "Developers", ("Full disks",), "Tidy", (("Speed", "Fast"),), (CLAIM,)
        ),
        angles=(
            Angle(
                "angle-1",
                "problem",
                "Junk",
                "Disks fill",
                "Slow builds",
                (CLAIM,),
                (Hook("hook-1-1", "Your disk is full", "question"),),
                (),
            ),
        ),
        post_ideas=(
            PostIdea(
                "idea-1",
                "angle-1",
                "hook-1-1",
                "carousel",
                "Clean fast",
                "Show speed",
                ("Problem", "Fix"),
                "A terminal",
                ("logo",),
                "learn_more",
                (CLAIM,),
                "",
            ),
        ),
        claims_to_avoid=(AvoidedClaim("Fastest ever", "superlative", "No proof"),),
        warnings=("One claim was dropped.",),
        input_tokens=100,
        output_tokens=50,
    )


def ideas_plan() -> IdeasPlan:
    return IdeasPlan(
        "claude_api", "Claude API", "claude-haiku-5-5", ("the README analysis",), 120, 900
    )


def post_copy() -> PostCopy:
    return PostCopy(
        platform="instagram",
        idea_id="idea-1",
        hook_id="hook-1-1",
        hook_text="Your disk is full",
        format="carousel",
        slides=(Slide("hook", "Your disk is full", "Clean it", "Terminal", "A terminal"),),
        caption=Caption("Tidy up", ("Run it",), "Try it"),
        alt_opening=AltOpening("Is your disk full?", "hook-1-1"),
        hashtags=("#python",),
        review_flags=(),
        warnings=(),
        input_tokens=80,
        output_tokens=40,
    )


def copy_plan() -> CopyPlan:
    return CopyPlan("claude_api", "Claude API", "claude-haiku-5-5", ("the idea",), 90, 700)


def design() -> Design:
    slide = SlideDesign("hook", "left", "none", "primary", "stars", "none", "cover", "", "")
    return Design("instagram", "idea-1", "hook-1-1", (slide,), None, ("Changed an icon.",), 70, 30)


def design_plan() -> DesignPlan:
    return DesignPlan("claude_api", "Claude API", "claude-haiku-5-5", ("the copy",), 95, 800, False)


def record(into: list[Any], item: Any, result: T) -> T:
    """Note what a stand-in was called with, then hand back its canned answer."""
    into.append(item)
    return result
