import json
from typing import Any

import pytest

from kodalo.core.settings.ai import AiConnectionError
from kodalo.core.studio.ideas import IdeasAssistant
from tests.api.studio import samples
from tests.cli.studio.conftest import Studio


@pytest.fixture
def asked(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Stand in for the AI and record what each call was asked."""
    calls: list[Any] = []
    monkeypatch.setattr(IdeasAssistant, "plan", lambda self, *args: samples.ideas_plan())
    monkeypatch.setattr(
        IdeasAssistant, "generate", lambda self, *args: samples.record(calls, args, samples.ideas())
    )
    monkeypatch.setattr(
        IdeasAssistant, "saved", lambda self, *args: samples.ideas() if calls else None
    )
    return calls


def test_studio_lists_its_steps(studio: Studio) -> None:
    code, out = studio.invoke("--help")

    assert code == 0
    for step in ("ideas", "copy", "design"):
        assert step in out


def test_plan_says_what_would_be_sent_and_sends_nothing(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.invoke("ideas", "plan", studio.repo_id)

    assert code == 0
    assert "the README analysis" in out
    assert "Claude API" in out
    assert "120 tokens in" in out
    assert asked == []


def test_plan_as_json(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.invoke("ideas", "plan", studio.repo_id, "--json")

    assert code == 0
    assert json.loads(out)["max_output_tokens"] == 900


def test_make_asks_first_and_shows_the_ideas(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.invoke("ideas", "make", studio.repo_id, input="y\n")

    assert code == 0
    assert "Continue?" in out
    for text in ("Awareness", "Your disk is full", "Clean fast", "Fastest ever", "No proof"):
        assert text in out
    assert "Used 100 tokens in, 50 out." in out
    assert "One claim was dropped." in out
    assert asked == [(studio.repo_id, "tool", "", "")]


def test_declining_sends_nothing(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.invoke("ideas", "make", studio.repo_id, input="n\n")

    assert code == 1
    assert "Nothing was sent." in out
    assert asked == []


def test_yes_skips_the_question_and_a_feature_post_names_its_focus(
    studio: Studio, asked: list[Any]
) -> None:
    code, out = studio.invoke(
        "ideas", "make", studio.repo_id, "--yes", "-t", "feature", "--kind", "features",
        "--name", "Scan", "--json",
    )  # fmt: skip

    assert code == 0
    assert "Continue?" not in out
    assert asked == [(studio.repo_id, "feature", "features", "Scan")]


def test_show_is_empty_until_ideas_were_made(studio: Studio, asked: list[Any]) -> None:
    code, out = studio.invoke("ideas", "show", studio.repo_id)
    assert (code, "No post ideas were made" in out) == (1, True)

    studio.invoke("ideas", "make", studio.repo_id, "--yes")
    code, out = studio.invoke("ideas", "show", studio.repo_id, "--json")

    assert code == 0
    assert json.loads(out)["post_ideas"][0]["id"] == "idea-1"


def test_an_unknown_post_type_is_a_usage_error(studio: Studio) -> None:
    assert studio.invoke("ideas", "show", studio.repo_id, "--type", "nope")[0] == 2


def test_ai_errors_are_short_messages(studio: Studio, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(self: object, *args: object) -> None:
        raise AiConnectionError("The AI could not be reached.")

    monkeypatch.setattr(IdeasAssistant, "plan", lambda self, *args: samples.ideas_plan())
    monkeypatch.setattr(IdeasAssistant, "generate", fail)

    code, out = studio.invoke("ideas", "make", studio.repo_id, "--yes")

    assert code == 1
    assert "The AI could not be reached." in out
    assert "Traceback" not in out
