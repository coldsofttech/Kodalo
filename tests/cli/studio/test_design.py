import json
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.studio.design import DesignAssistant
from tests.api.studio import samples
from tests.cli.studio.conftest import Studio


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Stand in for the AI and record the canvas each call was asked for."""
    calls: list[Any] = []
    monkeypatch.setattr(DesignAssistant, "plan", lambda self, choice, canvas: samples.design_plan())
    monkeypatch.setattr(
        DesignAssistant,
        "generate",
        lambda self, choice, canvas: samples.record(calls, canvas, samples.design()),
    )
    monkeypatch.setattr(
        DesignAssistant, "saved", lambda self, choice: samples.design() if calls else None
    )
    return calls


def test_plan_says_what_would_be_sent_and_sends_nothing(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("design", "plan")

    assert code == 0
    assert "the copy" in out
    assert "95 tokens in" in out
    assert asked == []


def test_make_designs_for_the_canvas_of_the_brand(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("design", "make", input="y\n")

    assert code == 0
    assert asked == [(1080, 1350)]
    for text in ("hook", "left", "stars", "template", "Changed an icon."):
        assert text in out
    assert "Used 70 tokens in, 30 out." in out


def test_declining_sends_nothing(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("design", "make", input="n\n")

    assert (code, "Nothing was sent." in out, asked) == (1, True, [])


def test_show_is_empty_until_a_design_was_made(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.post("design", "show")
    assert (code, "No design was made" in out) == (1, True)

    studio.post("design", "make", "--yes")
    code, out = studio.post("design", "show", "--json")

    assert code == 0
    assert json.loads(out)["slides"][0]["template"] == "hook"


def test_a_slide_is_written_to_a_file_or_to_the_screen(
    studio: Studio, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    modes: list[str] = []
    monkeypatch.setattr(
        DesignAssistant,
        "slide_page",
        lambda self, choice, index, brand, mode, assets: samples.record(
            modes, mode, "<p>Slide</p>"
        ),
    )
    target = tmp_path / "slide.html"

    code, _ = studio.post("design", "slide", "--slide", "2", "--mode", "dark", "-o", str(target))
    on_screen = studio.post("design", "slide")

    assert code == 0
    assert target.read_text(encoding="utf-8") == "<p>Slide</p>"
    assert on_screen[0] == 0
    assert "<p>Slide</p>" in on_screen[1]
    assert modes == ["dark", "light"]


def test_a_drawing_is_written_as_svg(
    studio: Studio, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        DesignAssistant, "svg", lambda self, choice, index: "<svg/>" if index == 0 else None
    )
    target = tmp_path / "drawing.svg"

    code, _ = studio.post("design", "svg", "--output", str(target))
    missing = studio.post("design", "svg", "--slide", "1")

    assert code == 0
    assert target.read_text(encoding="utf-8") == "<svg/>"
    assert (missing[0], "no drawing" in missing[1]) == (1, True)


def test_a_slide_without_a_saved_design_is_an_error(studio: Studio) -> None:
    code, out = studio.post("design", "slide")

    assert code == 1
    assert "no saved design" in out


def test_the_slide_number_and_mode_are_limited(studio: Studio) -> None:
    assert studio.post("design", "slide", "--slide", "12")[0] == 2
    assert studio.post("design", "svg", "--slide", "-1")[0] == 2
    assert studio.post("design", "slide", "--mode", "sepia")[0] == 2


@pytest.mark.usefixtures("unsupported_canvas")
def test_a_design_is_only_made_for_supported_platforms(studio: Studio) -> None:
    code, out = studio.post("design", "plan")

    assert code == 1
    assert "tiktok" in out
