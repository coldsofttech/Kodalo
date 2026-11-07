from typing import Any

import pytest

from tests.api.studio import samples
from tests.api.studio.conftest import Studio


def test_design_is_planned_made_and_returned_again(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    sizes: list[Any] = []
    monkeypatch.setattr(
        services.design,
        "plan",
        lambda choice, canvas: samples.record(sizes, canvas, samples.design_plan()),
    )
    monkeypatch.setattr(services.design, "generate", lambda choice, canvas: samples.design())
    monkeypatch.setattr(services.design, "saved", lambda choice: samples.design())

    plan = studio.client.post(f"{studio.url}/design/plan", json=studio.ask())
    made = studio.client.post(f"{studio.url}/design", json=studio.ask())
    again = studio.client.get(f"{studio.url}/design", params=studio.ask())

    assert plan.json()["max_output_tokens"] == 800
    assert sizes == [(1080, 1350)]  # the canvas of the brand
    body = made.json()
    assert body["slides"][0] | {} == {
        "template": "hook",
        "align": "left",
        "media": "none",
        "accent": "primary",
        "icon": "stars",
        "image_source": "none",
        "image_fit": "cover",
        "has_svg": False,
        "has_html": False,
    }
    assert body["warnings"] == ["Changed an icon."]
    assert again.json() == body


def test_a_design_that_was_not_made_is_404(studio: Studio) -> None:
    assert studio.client.get(f"{studio.url}/design", params=studio.ask()).status_code == 404
    for kind in ("slide", "svg"):
        response = studio.client.get(
            f"{studio.url}/design/{kind}", params={**studio.ask(), "slide": 0}
        )
        assert response.status_code == 404


def test_a_slide_page_is_served_with_a_policy_that_runs_nothing(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    modes: list[str] = []
    monkeypatch.setattr(
        services.design,
        "slide_page",
        lambda choice, index, brand, mode, assets: samples.record(modes, mode, "<p>Slide</p>"),
    )

    light = studio.client.get(f"{studio.url}/design/slide", params={**studio.ask(), "slide": 0})
    dark = studio.client.get(
        f"{studio.url}/design/slide", params={**studio.ask(), "slide": 0, "mode": "dark"}
    )

    assert light.status_code == 200
    assert light.text == "<p>Slide</p>"
    assert light.headers["content-type"].startswith("text/html")
    assert "default-src 'none'" in light.headers["content-security-policy"]
    assert (light.headers["x-content-type-options"], light.headers["cache-control"]) == (
        "nosniff",
        "no-store",
    )
    assert dark.status_code == 200
    assert modes == ["light", "dark"]


def test_a_drawing_is_served_as_svg(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        services.design, "svg", lambda choice, index: "<svg/>" if index == 0 else None
    )

    drawing = studio.client.get(f"{studio.url}/design/svg", params={**studio.ask(), "slide": 0})
    missing = studio.client.get(f"{studio.url}/design/svg", params={**studio.ask(), "slide": 1})

    assert drawing.status_code == 200
    assert drawing.headers["content-type"].startswith("image/svg+xml")
    assert "default-src 'none'" in drawing.headers["content-security-policy"]
    assert drawing.text == "<svg/>"
    assert missing.status_code == 404


def test_the_slide_number_is_limited(studio: Studio) -> None:
    for kind in ("slide", "svg"):
        for number in (-1, 12):
            response = studio.client.get(
                f"{studio.url}/design/{kind}", params={**studio.ask(), "slide": number}
            )
            assert response.status_code == 422
    bad_mode = {**studio.ask(), "slide": 0, "mode": "sepia"}
    assert studio.client.get(f"{studio.url}/design/slide", params=bad_mode).status_code == 422


def test_design_needs_an_existing_brand(studio: Studio) -> None:
    ask = studio.ask(brand_id="nope")

    responses = [
        studio.client.get(f"{studio.url}/design", params=ask),
        studio.client.get(f"{studio.url}/design/svg", params={**ask, "slide": 0}),
        studio.client.get(f"{studio.url}/design/slide", params={**ask, "slide": 0}),
        studio.client.post(f"{studio.url}/design/plan", json=ask),
        studio.client.post(f"{studio.url}/design", json=ask),
    ]

    assert [r.status_code for r in responses] == [404, 404, 404, 404, 404]


@pytest.mark.usefixtures("custom_canvas")
def test_a_design_is_only_made_for_instagram(studio: Studio) -> None:
    plan = studio.client.post(f"{studio.url}/design/plan", json=studio.ask())
    made = studio.client.post(f"{studio.url}/design", json=studio.ask())

    assert (plan.status_code, made.status_code) == (422, 422)
