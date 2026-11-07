"""Writing the copy of a post idea with the AI, keeping it, and editing it."""

import json
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from kodalo.core.ai import AiTarget, Generation
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.platforms import Platforms
from kodalo.core.storage import Database, database_path
from kodalo.core.storage.models import Repository
from kodalo.core.studio import copy as cp
from kodalo.core.studio.copy import Caption, Choice, CopyAssistant, Slide
from kodalo.core.studio.ideas import (
    Angle,
    AvoidedClaim,
    Claim,
    Hook,
    Ideas,
    PostIdea,
    Strategy,
)

CLAIM = Claim("Runs after commits", "README.md", "post-commit cleanup", False)
CHOICE = Choice("instagram", "r1", "feature", "features", "Hooks", "idea-1", "")

REPLY: dict[str, Any] = {
    "slides": [
        {
            "role": "hook",
            "headline": "What if cleanup ran after each commit?",
            "body": "",
            "visual_note": "A commit timeline",
            "alt_text": "A timeline of commits",
        },
        {
            "role": "cta",
            "headline": "Read the docs",
            "body": "Set it up.",
            "visual_note": "",
            "alt_text": "",
        },
    ],
    "caption": {
        "opening": "What if cleanup ran after each commit?",
        "body": ["One hook."],
        "cta": "Read the docs.",
    },
    "alt_opening": {"text": "Cleanup after commits", "hook_id": "hook-1-2"},
    "hashtags": ["#Sweepito", "sweepito", "#git hooks"],
    "review_flags": [{"type": "bogus", "text": "A sentence", "reason": "Check it"}],
}


def _ideas(format_: str = "carousel") -> Ideas:
    idea = PostIdea(
        "idea-1",
        "angle-1",
        "hook-1-1",
        format_,
        "Cleanup after every commit",
        "Objective",
        ("One", "Two"),
        "Visual",
        ("Logo",),
        "read_docs",
        (CLAIM,),
        "",
    )
    angle = Angle(
        "angle-1",
        "workflow_fit",
        "Workflow",
        "Summary",
        "Pain",
        (CLAIM,),
        (
            Hook("hook-1-1", "What if cleanup ran after each commit?", "question"),
            Hook("hook-1-2", "Cleanup after commits", "bold_statement"),
        ),
        (),
    )
    strategy = Strategy("Objective", "Developers", (), "Positioning", (), ())
    return Ideas(
        "feature",
        "Hooks",
        strategy,
        (angle,),
        (idea,),
        (AvoidedClaim("17 profiles", "number", ""),),
        (),
        1,
        1,
    )


class FakeAi:
    def __init__(self, reply: object) -> None:
        self.reply = reply
        self.calls = 0

    def default_target(self) -> AiTarget:
        return AiTarget("claude_api", "Claude API", "haiku", None, 0.0, 30)

    def generate(self, system: str, prompt: str, max_tokens: int, **kwargs: Any) -> Generation:
        self.calls += 1
        self.prompt = prompt
        return Generation(json.dumps(self.reply), 10, 20)


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path / "data"))
    with db.session() as session:
        session.add(Repository(id="r1", url="https://github.com/o/r", owner="o", name="r"))
    yield db
    db.close()


def _assistant(database: Database, ai: FakeAi, ideas: Ideas | None = None) -> CopyAssistant:
    found = ideas if ideas is not None else _ideas()
    return CopyAssistant(
        SimpleNamespace(get=lambda _id: SimpleNamespace(tagline="Tag", summary="Sum")),  # type: ignore[arg-type]
        SimpleNamespace(get=lambda _id: SimpleNamespace(name="Sweepito")),  # type: ignore[arg-type]
        SimpleNamespace(saved=lambda *args: found),  # type: ignore[arg-type]
        ai,  # type: ignore[arg-type]
        Platforms(database),
        database,
    )


def test_the_prompt_for_instagram_is_bundled() -> None:
    assert "Instagram post" in cp.system_prompt("instagram")


def test_the_copy_is_written_cleaned_and_kept(database: Database) -> None:
    ai = FakeAi(REPLY)
    assistant = _assistant(database, ai)

    assert assistant.saved(CHOICE) is None
    post = assistant.generate(CHOICE)

    assert post.hook_id == "hook-1-1"
    assert next(s.headline for s in post.slides) == "What if cleanup ran after each commit?"
    assert post.hashtags == ("#sweepito", "#githooks")
    assert post.review_flags[0].type == "other"
    assert (post.input_tokens, post.output_tokens) == (10, 20)
    assert "alternative_hooks" in ai.prompt
    assert "17 profiles" in ai.prompt
    assert assistant.saved(CHOICE) == post


def test_single_image_keeps_one_slide(database: Database) -> None:
    assistant = _assistant(database, FakeAi(REPLY), _ideas("single_image"))

    assert len(assistant.generate(CHOICE).slides) == 1


def test_a_statement_to_avoid_is_warned_about(database: Database) -> None:
    reply = {**REPLY, "caption": {**REPLY["caption"], "body": ["Includes 17 profiles."]}}

    post = _assistant(database, FakeAi(reply)).generate(CHOICE)

    assert post.warnings == ("The copy repeats a statement to use with care: 17 profiles",)


def test_a_reply_without_slides_is_rejected(database: Database) -> None:
    with pytest.raises(AiInvalidError):
        _assistant(database, FakeAi({"slides": []})).generate(CHOICE)


def test_unknown_idea_hook_and_platform_are_rejected(database: Database) -> None:
    assistant = _assistant(database, FakeAi(REPLY))

    with pytest.raises(RepoNotFoundError):
        assistant.plan(Choice("instagram", "r1", "feature", "features", "Hooks", "idea-9", ""))
    with pytest.raises(AiInvalidError):
        assistant.plan(
            Choice("instagram", "r1", "feature", "features", "Hooks", "idea-1", "hook-9")
        )
    with pytest.raises(AiInvalidError):
        assistant.plan(Choice("tiktok", "r1", "feature", "features", "Hooks", "idea-1", ""))


def test_the_plan_says_what_is_sent(database: Database) -> None:
    plan = _assistant(database, FakeAi(REPLY)).plan(CHOICE)

    assert plan.items == ("Cleanup after every commit",)
    assert plan.input_tokens > 0


def test_an_edit_replaces_the_saved_text(database: Database) -> None:
    assistant = _assistant(database, FakeAi(REPLY))

    with pytest.raises(RepoNotFoundError):
        assistant.edit(CHOICE, (Slide("hook", "x", "", "", ""),), Caption("o", (), "c"), "a", ())

    made = assistant.generate(CHOICE)
    edited = assistant.edit(
        CHOICE,
        (Slide("hook", "My headline", "", "", ""),),
        Caption("My opening", ("Line",), "Go"),
        "Other opening",
        ("#One", "two"),
    )

    assert edited.slides[0].headline == "My headline"
    assert edited.caption.opening == "My opening"
    assert edited.alt_opening.hook_id == made.alt_opening.hook_id
    assert edited.hashtags == ("#one", "#two")
    assert assistant.saved(CHOICE) == edited


def test_the_saved_json_gives_back_the_same_copy(database: Database) -> None:
    post = _assistant(database, FakeAi(REPLY)).generate(CHOICE)

    assert cp._post_from_json(json.dumps(asdict(post))) == post


def test_the_platform_settings_decide_the_hashtags(database: Database) -> None:
    Platforms(database).save("instagram", 3, ["#Mine"])
    ai = FakeAi({**REPLY, "hashtags": ["#a", "#b", "#c", "#d"]})

    post = _assistant(database, ai).generate(CHOICE)

    assert '"hashtag_count": 2' in ai.prompt
    assert '"#mine"' in ai.prompt
    assert post.hashtags == ("#mine", "#a", "#b")
