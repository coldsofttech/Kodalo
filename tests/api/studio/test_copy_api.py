from typing import Any

import pytest

from kodalo.core.settings.ai import AiInvalidError
from tests.api.studio import samples
from tests.api.studio.conftest import Studio


def test_copy_is_planned_made_and_returned_again(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen: list[Any] = []
    monkeypatch.setattr(services.copy, "plan", lambda choice: samples.copy_plan())
    monkeypatch.setattr(
        services.copy,
        "generate",
        lambda choice: samples.record(chosen, choice, samples.post_copy()),
    )
    monkeypatch.setattr(
        services.copy, "saved", lambda choice: samples.post_copy() if chosen else None
    )

    assert studio.client.get(f"{studio.url}/copy", params=studio.ask()).status_code == 404
    plan = studio.client.post(f"{studio.url}/copy/plan", json=studio.ask())
    made = studio.client.post(f"{studio.url}/copy", json=studio.ask(hook_id="hook-1-1"))
    again = studio.client.get(f"{studio.url}/copy", params=studio.ask(hook_id="hook-1-1"))

    assert plan.json()["max_output_tokens"] == 700
    body = made.json()
    assert (body["platform"], body["format"], body["hashtags"]) == (
        "instagram",
        "carousel",
        ["#python"],
    )
    assert body["slides"][0]["headline"] == "Your disk is full"
    assert body["caption"]["cta"] == "Try it"
    assert again.json() == body
    choice = chosen[0]
    assert (choice.platform, choice.repo_id, choice.idea_id, choice.hook_id) == (
        "instagram",
        studio.repo_id,
        "idea-1",
        "hook-1-1",
    )


def test_edited_copy_replaces_the_saved_copy(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    edited = {
        **studio.ask(),
        "slides": [
            {
                "role": "hook",
                "headline": "New headline",
                "body": "New body",
                "visual_note": "Note",
                "alt_text": "Alt",
            }
        ],
        "caption": {"opening": "Open", "body": ["Line"], "cta": "Go"},
        "alt_opening": "Other opening",
        "hashtags": ["#new"],
    }
    assert studio.client.put(f"{studio.url}/copy", json=edited).status_code == 404  # nothing yet

    monkeypatch.setattr(services.copy, "saved", lambda choice: samples.post_copy())
    monkeypatch.setattr(services.copy, "_save", lambda choice, post: None)
    response = studio.client.put(f"{studio.url}/copy", json=edited)

    assert response.status_code == 200
    body = response.json()
    assert body["slides"][0]["headline"] == "New headline"
    assert body["caption"]["opening"] == "Open"
    assert body["alt_opening"]["text"] == "Other opening"
    assert "#new" in body["hashtags"]


def test_copy_validates_the_request(studio: Studio) -> None:
    bad = {**studio.ask(), "idea_id": ""}
    assert studio.client.post(f"{studio.url}/copy", json=bad).status_code == 422
    assert studio.client.post(f"{studio.url}/copy/plan", json={}).status_code == 422
    assert studio.client.get(f"{studio.url}/copy").status_code == 422
    no_slides = {**studio.ask(), "slides": [], "caption": {"opening": "", "body": [], "cta": ""}}
    assert studio.client.put(f"{studio.url}/copy", json=no_slides).status_code == 422


def test_copy_needs_an_existing_brand(studio: Studio) -> None:
    ask = studio.ask(brand_id="nope")

    saved = studio.client.get(f"{studio.url}/copy", params=ask)
    plan = studio.client.post(f"{studio.url}/copy/plan", json=ask)
    made = studio.client.post(f"{studio.url}/copy", json=ask)

    assert (saved.status_code, plan.status_code, made.status_code) == (404, 404, 404)


@pytest.mark.usefixtures("unsupported_canvas")
def test_copy_is_only_written_for_supported_platforms(studio: Studio) -> None:
    responses = [
        studio.client.get(f"{studio.url}/copy", params=studio.ask()),
        studio.client.post(f"{studio.url}/copy/plan", json=studio.ask()),
        studio.client.post(f"{studio.url}/copy", json=studio.ask()),
    ]

    assert [r.status_code for r in responses] == [422, 422, 422]
    assert "tiktok" in responses[0].json()["detail"]


@pytest.mark.usefixtures("custom_canvas")
def test_copy_is_written_for_a_custom_canvas(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen: list[Any] = []
    monkeypatch.setattr(
        services.copy,
        "generate",
        lambda choice: samples.record(chosen, choice, samples.post_copy()),
    )

    made = studio.client.post(f"{studio.url}/copy", json=studio.ask(hook_id="hook-1-1"))

    assert made.status_code == 200
    assert chosen[0].platform == "custom"


def test_ai_errors_while_writing_become_http_errors(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(choice: object) -> None:
        raise AiInvalidError("The AI answer was not usable.")

    monkeypatch.setattr(services.copy, "generate", fail)

    response = studio.client.post(f"{studio.url}/copy", json=studio.ask())

    assert response.status_code == 422
    assert response.json()["detail"] == "The AI answer was not usable."
