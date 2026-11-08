from dataclasses import replace
from typing import Any

import pytest

from kodalo.core.settings.ai import AiConnectionError, AiInvalidError
from tests.api.studio import samples
from tests.api.studio.conftest import Studio

TOOL = {"post_type": "tool"}


def test_saved_ideas_are_404_until_the_ai_made_some(studio: Studio) -> None:
    response = studio.client.get(f"{studio.url}/ideas", params=TOOL)

    assert response.status_code == 404


def test_ideas_are_planned_made_and_returned_again(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    made_for: list[Any] = []
    monkeypatch.setattr(services.ideas, "plan", lambda *args: samples.ideas_plan())
    monkeypatch.setattr(
        services.ideas, "generate", lambda *args: samples.record(made_for, args, samples.ideas())
    )
    monkeypatch.setattr(
        services.ideas, "saved", lambda *args: samples.ideas() if made_for else None
    )

    plan = studio.client.post(f"{studio.url}/ideas/plan", json=TOOL)
    made = studio.client.post(f"{studio.url}/ideas", json=TOOL)
    again = studio.client.get(f"{studio.url}/ideas", params=TOOL)

    assert plan.status_code == 200
    assert (plan.json()["label"], plan.json()["input_tokens"]) == ("Claude API", 120)
    assert made.status_code == 200
    body = made.json()
    assert [i["id"] for i in body["post_ideas"]] == ["idea-1"]
    assert body["angles"][0]["hooks"][0]["id"] == "hook-1-1"
    assert body["claims_to_avoid"][0]["reason"] == "No proof"
    assert made_for == [(studio.repo_id, "tool", "", "")]
    assert again.json() == body


def test_a_feature_post_passes_its_focus_on(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Any] = []
    monkeypatch.setattr(
        services.ideas, "generate", lambda *args: samples.record(seen, args, samples.ideas())
    )
    body = {"post_type": "feature", "kind": "features", "name": "Scan"}

    studio.client.post(f"{studio.url}/ideas", json=body)

    assert seen == [(studio.repo_id, "feature", "features", "Scan")]


def test_ideas_validate_the_request(studio: Studio) -> None:
    for body in ({"post_type": "nope"}, {"post_type": "tool", "kind": "nope"}, {}):
        assert studio.client.post(f"{studio.url}/ideas", json=body).status_code == 422
        assert studio.client.post(f"{studio.url}/ideas/plan", json=body).status_code == 422
    assert studio.client.get(f"{studio.url}/ideas").status_code == 422


def test_ideas_of_an_unknown_repository_are_404(studio: Studio) -> None:
    url = "/api/v1/studio/repositories/missing/ideas"

    assert studio.client.post(f"{url}/plan", json=TOOL).status_code == 404
    assert studio.client.post(url, json=TOOL).status_code == 404
    assert studio.client.get(url, params=TOOL).status_code == 404


def test_the_ideas_need_a_readme_analysis_first(studio: Studio) -> None:
    response = studio.client.post(f"{studio.url}/ideas/plan", json=TOOL)

    assert response.status_code in (404, 422)


@pytest.mark.parametrize(
    ("error", "status_code"),
    [(AiInvalidError("Bad answer."), 422), (AiConnectionError("Unreachable."), 502)],
)
def test_ai_errors_become_http_errors(
    studio: Studio,
    services: Any,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
) -> None:
    def fail(*args: object) -> None:
        raise error

    monkeypatch.setattr(services.ideas, "generate", fail)

    response = studio.client.post(f"{studio.url}/ideas", json=TOOL)

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)


def test_an_idea_is_flagged_as_posted(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Any] = []
    flagged = samples.ideas().post_ideas[0]
    monkeypatch.setattr(
        services.ideas,
        "mark_posted",
        lambda *args: samples.record(seen, args, replace(flagged, posted=args[-1])),
    )

    response = studio.client.put(f"{studio.url}/ideas/idea-1/posted", json={**TOOL, "posted": True})

    assert response.status_code == 200
    assert response.json()["posted"] is True
    assert seen == [(studio.repo_id, "tool", "", "", "idea-1", True)]


def test_flagging_an_unsaved_idea_is_404(studio: Studio) -> None:
    response = studio.client.put(f"{studio.url}/ideas/idea-1/posted", json={**TOOL, "posted": True})

    assert response.status_code == 404


def test_ideas_can_grow_past_the_first_five(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = samples.ideas()
    many = replace(
        first,
        angles=first.angles * 4,
        post_ideas=tuple(replace(first.post_ideas[0], id=f"idea-{n}") for n in range(1, 13)),
    )
    monkeypatch.setattr(services.ideas, "saved", lambda *args: many)

    response = studio.client.get(f"{studio.url}/ideas", params=TOOL)

    assert response.status_code == 200
    assert len(response.json()["post_ideas"]) == 12
    assert len(response.json()["angles"]) == 4
