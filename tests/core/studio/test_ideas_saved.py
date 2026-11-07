"""Keeping the post ideas the AI made, so they are shown again instead of asked for again."""

from collections.abc import Iterator
from dataclasses import asdict, replace
from pathlib import Path

import pytest

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
