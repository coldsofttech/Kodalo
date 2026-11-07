import json
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.studio.copy import CopyAssistant
from tests.api.studio import samples
from tests.cli.studio.conftest import Studio


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Stand in for the AI and record which idea each call was asked for."""
    calls: list[Any] = []
    monkeypatch.setattr(CopyAssistant, "plan", lambda self, choice: samples.copy_plan())
    monkeypatch.setattr(
        CopyAssistant,
        "generate",
        lambda self, choice: samples.record(calls, choice, samples.post_copy()),
    )
    monkeypatch.setattr(
        CopyAssistant, "saved", lambda self, choice: samples.post_copy() if calls else None
    )
    return calls


def test_plan_says_what_would_be_sent_and_sends_nothing(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("copy", "plan")

    assert code == 0
    assert "the idea" in out
    assert "90 tokens in" in out
    assert asked == []


def test_make_shows_the_slides_caption_and_hashtags(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("copy", "make", "--hook", "hook-1-1", input="y\n")

    assert code == 0
    for text in (
        "Your disk is full",
        "Clean it",
        "Tidy up",
        "Try it",
        "Is your disk full?",
        "#python",
    ):
        assert text in out
    assert "Used 80 tokens in, 40 out." in out
    choice = asked[0]
    assert (choice.platform, choice.repo_id, choice.idea_id, choice.hook_id) == (
        "instagram",
        studio.repo_id,
        "idea-1",
        "hook-1-1",
    )


def test_declining_sends_nothing(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("copy", "make", input="n\n")

    assert (code, "Nothing was sent." in out, asked) == (1, True, [])


def test_show_is_empty_until_copy_was_written(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("copy", "show")
    assert (code, "No copy was written" in out) == (1, True)

    studio.post("copy", "make", "--yes")
    code, out = studio.post("copy", "show", "--json")

    assert code == 0
    assert json.loads(out)["caption"]["cta"] == "Try it"


def test_edit_replaces_the_copy_with_the_text_of_a_file(
    studio: Studio, asked: list[Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    saved: list[Any] = []
    monkeypatch.setattr(CopyAssistant, "_save", lambda self, choice, post: saved.append(post))
    studio.post("copy", "make", "--yes")
    shown = json.loads(studio.post("copy", "show", "--json")[1])
    shown["slides"][0]["headline"] = "Edited headline"
    shown["hashtags"] = ["#edited"]
    path = tmp_path / "copy.json"
    path.write_text(json.dumps(shown), encoding="utf-8")

    code, out = studio.post("copy", "edit", "--file", str(path))

    assert code == 0
    assert "Edited headline" in out
    assert saved[0].hashtags == ("#edited",)
    assert saved[0].alt_opening.text == "Is your disk full?"


def test_edit_refuses_a_file_it_cannot_read(
    studio: Studio, asked: list[Any], tmp_path: Path
) -> None:
    studio.post("copy", "make", "--yes")
    path = tmp_path / "copy.json"
    path.write_text('{"slides": []}', encoding="utf-8")

    code, out = studio.post("copy", "edit", "--file", str(path))

    assert code == 1
    assert "Cannot read the edited copy" in out


def test_edit_needs_a_file_that_exists(studio: Studio, tmp_path: Path) -> None:
    assert studio.post("copy", "edit", "--file", str(tmp_path / "missing.json"))[0] == 2


def test_an_unknown_brand_is_an_error(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.invoke("copy", "plan", studio.repo_id, "--brand", "Nope", "--idea", "idea-1")

    assert code == 1
    assert out.strip()


@pytest.mark.usefixtures("custom_canvas")
def test_copy_is_only_written_for_instagram(studio: Studio) -> None:
    code, out = studio.post("copy", "plan")

    assert code == 1
    assert "Instagram" in out


def test_brand_and_idea_are_required(studio: Studio) -> None:
    assert studio.invoke("copy", "plan", studio.repo_id)[0] == 2
