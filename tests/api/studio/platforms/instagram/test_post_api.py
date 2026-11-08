from typing import Any

import pytest

from tests.api.studio.conftest import Studio


def test_a_designed_post_is_posted_in_the_chosen_mode(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kodalo.core.settings.platforms import PublishedPost

    seen: list[Any] = []

    def post(choice: Any, brand: Any, assets: Any, mode: str) -> PublishedPost:
        seen.append((choice.idea_id, brand.canvas.platform_id, mode))
        return PublishedPost("m1", "https://www.instagram.com/p/x/")

    monkeypatch.setattr(services.poster, "post", post)

    response = studio.client.post(
        f"{studio.url}/design/post", json={**studio.ask(), "mode": "dark"}
    )

    assert response.status_code == 200
    assert response.json() == {"media_id": "m1", "permalink": "https://www.instagram.com/p/x/"}
    assert seen[0][2] == "dark"


@pytest.mark.parametrize(
    ("error", "code"),
    [
        ("studio", 422),
        ("invalid", 422),
        ("connection", 502),
        ("tunnel", 502),
        ("secret", 503),
        ("render", 503),
    ],
)
def test_a_post_that_fails_says_why_without_details(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch, error: str, code: int
) -> None:
    from kodalo.core.parsers.image.render import RenderError
    from kodalo.core.settings.platforms import (
        PlatformConnectionError,
        PlatformInvalidError,
        PlatformSecretError,
    )
    from kodalo.core.studio import StudioInvalidError
    from kodalo.core.tunnel import TunnelError

    errors = {
        "studio": StudioInvalidError("Posting is only available for Instagram canvases."),
        "invalid": PlatformInvalidError("The caption is too long."),
        "connection": PlatformConnectionError("Instagram refused the post."),
        "tunnel": TunnelError("cloudflared did not give a public address in time."),
        "secret": PlatformSecretError("The keychain is not available."),
        "render": RenderError("Microsoft Edge is needed."),
    }

    def post(*args: Any) -> None:
        raise errors[error]

    monkeypatch.setattr(services.poster, "post", post)

    response = studio.client.post(f"{studio.url}/design/post", json=studio.ask())

    assert response.status_code == code
    assert response.json()["detail"] == str(errors[error])


def test_a_designed_post_is_exported_into_the_chosen_folder(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    from kodalo.core.studio.platforms.instagram.post import ExportedPost

    seen: list[Any] = []

    def export(choice: Any, brand: Any, assets: Any, folder: str, mode: str) -> ExportedPost:
        seen.append((folder, mode))
        target = Path(folder) / "post"
        return ExportedPost(target, (target / "slide-1.jpg",), target / "caption.txt")

    monkeypatch.setattr(services.poster, "export", export)

    response = studio.client.post(
        f"{studio.url}/design/export", json={**studio.ask(), "mode": "dark", "folder": "C:/Posts"}
    )

    assert response.status_code == 200
    assert seen == [("C:/Posts", "dark")]
    body = response.json()
    assert body["folder"].endswith("post")
    assert [p.endswith("slide-1.jpg") for p in body["pictures"]] == [True]
    assert body["caption_file"].endswith("caption.txt")


def test_an_export_needs_a_folder(studio: Studio) -> None:
    missing = studio.client.post(f"{studio.url}/design/export", json=studio.ask())
    too_long = studio.client.post(
        f"{studio.url}/design/export", json={**studio.ask(), "folder": "x" * 1025}
    )

    assert (missing.status_code, too_long.status_code) == (422, 422)


@pytest.mark.parametrize(("error", "code"), [("studio", 422), ("render", 503)])
def test_an_export_that_fails_says_why_without_details(
    studio: Studio, services: Any, monkeypatch: pytest.MonkeyPatch, error: str, code: int
) -> None:
    from kodalo.core.parsers.image.render import RenderError
    from kodalo.core.studio import StudioInvalidError

    errors = {
        "studio": StudioInvalidError("Choose a folder that exists."),
        "render": RenderError("Microsoft Edge is needed."),
    }

    def export(*args: Any) -> None:
        raise errors[error]

    monkeypatch.setattr(services.poster, "export", export)

    response = studio.client.post(
        f"{studio.url}/design/export", json={**studio.ask(), "folder": "C:/Posts"}
    )

    assert response.status_code == code
    assert response.json()["detail"] == str(errors[error])
