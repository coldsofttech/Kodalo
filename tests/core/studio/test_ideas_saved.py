"""Keeping the post ideas the AI made, so they are shown again instead of asked for again."""

from collections.abc import Iterator
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from kodalo.core.repositories import RepoNotFoundError
from kodalo.core.storage import Database, database_path
from kodalo.core.storage.models import Repository
from kodalo.core.studio import ideas as ideas_module
from kodalo.core.studio.ideas import (
    Angle,
    AvoidedClaim,
    Claim,
    Hook,
    Ideas,
    IdeasAssistant,
    PostIdea,
    Strategy,
)

CLAIM = Claim("Fast", "README.md", "It is fast.", False)


def _ideas(title: str = "Where the space went") -> Ideas:
    return Ideas(
        "feature",
        "Cleanup",
        Strategy(
            "Objective",
            "Developers",
            ("Full disks",),
            "Positioning",
            (("Speed", "Fast"),),
            (CLAIM,),
        ),
        (
            Angle(
                "angle-1",
                "pain",
                "Space",
                "Summary",
                "Pain",
                (CLAIM,),
                (Hook("hook-1", "Why?", "q"),),
                ("Care",),
            ),
        ),
        (
            PostIdea(
                "idea-1",
                "angle-1",
                "hook-1",
                "carousel",
                title,
                "Objective",
                ("One", "Two"),
                "Visual",
                ("Logo",),
                "follow",
                (CLAIM,),
                "",
            ),
        ),
        (AvoidedClaim("17 profiles", "count", "May change"),),
        ("A warning",),
        100,
        200,
    )


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path / "data"))
    with db.session() as session:
        session.add(Repository(id="r1", url="https://github.com/o/r", owner="o", name="r"))
    yield db
    db.close()


def test_the_saved_json_gives_back_the_same_ideas() -> None:
    made = _ideas()

    import json

    assert ideas_module._ideas_from_json(json.dumps(asdict(made))) == made


def test_ideas_are_saved_for_a_focus_and_replaced_by_a_refresh(database: Database) -> None:
    assistant = IdeasAssistant(None, None, database)  # type: ignore[arg-type]

    assert assistant.saved("r1", "feature", "features", "Cleanup") is None

    assistant._save("r1", "feature", "features", "Cleanup", _ideas())
    assert assistant.saved("r1", "feature", "features", "Cleanup") == _ideas()
    assert assistant.saved("r1", "feature", "features", "Other") is None
    assert assistant.saved("r1", "tool") is None

    newer = replace(_ideas("Marker files first"))
    assistant._save("r1", "feature", "features", "Cleanup", newer)
    saved = assistant.saved("r1", "feature", "features", "Cleanup")
    assert saved is not None
    assert saved.post_ideas[0].working_title == "Marker files first"


def test_a_refresh_adds_new_ideas_and_skips_ones_already_made() -> None:
    old = _ideas("Where the space went")
    fresh = _ideas("where  the space went")
    other = _ideas("Marker files first").post_ideas[0]
    new = replace(fresh, post_ideas=(fresh.post_ideas[0], other))

    merged = ideas_module._merge(old, new)

    assert [i.working_title for i in merged.post_ideas] == [
        "Where the space went",
        "Marker files first",
    ]
    assert merged.post_ideas[0] is old.post_ideas[0]
    assert merged.post_ideas[1].id == "idea-2"
    assert merged.strategy == old.strategy
    assert any("already made" in w for w in merged.warnings)


def test_a_refresh_reuses_a_matching_angle_and_adds_new_hooks() -> None:
    old = _ideas()
    angle = old.angles[0]
    new_angle = replace(
        angle, id="angle-9", hooks=(Hook("hook-1", "Why?", "q"), Hook("hook-2", "How?", "q"))
    )
    idea = replace(
        old.post_ideas[0], id="idea-1", working_title="New", angle_id="angle-9", hook_id="hook-2"
    )

    merged = ideas_module._merge(old, replace(old, angles=(new_angle,), post_ideas=(idea,)))

    assert [a.id for a in merged.angles] == ["angle-1"]
    assert [h.id for h in merged.angles[0].hooks] == ["hook-1", "hook-2"]
    assert (merged.post_ideas[1].angle_id, merged.post_ideas[1].hook_id) == ("angle-1", "hook-2")
    assert merged.post_ideas[1].id == "idea-2"


def test_an_idea_can_be_flagged_as_posted_and_stays_so_after_a_refresh(
    database: Database,
) -> None:
    assistant = IdeasAssistant(None, None, database)  # type: ignore[arg-type]
    assistant._save("r1", "tool", "", "", _ideas())

    assert assistant.mark_posted("r1", "tool", "", "", "idea-1", True).posted is True
    saved = assistant.saved("r1", "tool")
    assert saved is not None
    assert saved.post_ideas[0].posted is True

    merged = ideas_module._merge(saved, _ideas("Marker files first"))
    assert [i.posted for i in merged.post_ideas] == [True, False]

    assert assistant.mark_posted("r1", "tool", "", "", "idea-1", False).posted is False
    with pytest.raises(RepoNotFoundError):
        assistant.mark_posted("r1", "tool", "", "", "nope", True)
