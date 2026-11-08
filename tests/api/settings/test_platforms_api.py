from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

URL = "/api/v1/settings/platforms/instagram"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_defaults_then_saved(client: TestClient) -> None:
    assert client.get(URL).json() == {
        "platform": "instagram",
        "hashtag_count": 5,
        "default_hashtags": [],
        "use_social_preview": False,
        "use_repo_icon": False,
        "use_icons": False,
        "build_custom_images": False,
        "use_ai_templates": False,
    }

    saved = client.put(
        URL,
        json={"hashtag_count": 10, "default_hashtags": ["#Sweepito"], "use_icons": True},
    )

    assert saved.json()["default_hashtags"] == ["#sweepito"]
    assert client.get(URL).json()["hashtag_count"] == 10
    assert client.get(URL).json()["use_icons"] is True


def test_custom_has_its_own_settings(client: TestClient) -> None:
    custom = "/api/v1/settings/platforms/custom"

    saved = client.put(custom, json={"hashtag_count": 3, "default_hashtags": ["#Kodalo"]})

    assert saved.json()["platform"] == "custom"
    assert client.get(custom).json()["default_hashtags"] == ["#kodalo"]
    assert client.get(URL).json()["hashtag_count"] == 5


def test_a_bad_request_is_refused(client: TestClient) -> None:
    too_many = client.put(URL, json={"hashtag_count": 1, "default_hashtags": ["#a", "#b"]})

    assert too_many.status_code == 422
    assert client.put(URL, json={"hashtag_count": 31, "default_hashtags": []}).status_code == 422
    assert client.get("/api/v1/settings/platforms/tiktok").status_code == 422


CONNECTION = "/api/v1/settings/platforms/instagram/connection"


def test_instagram_connection_never_returns_the_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "kodalo.core.settings.platforms.instagram._fetch_profile",
        lambda token, account_id: {"id": account_id, "username": "sweepito"},
    )
    assert client.get(CONNECTION).json()["connected"] is False
    assert client.post(f"{CONNECTION}/check").status_code == 404

    connected = client.put(
        CONNECTION, json={"access_token": "IGAA-secret-1234", "account_id": "1784140"}
    )

    assert connected.status_code == 200
    assert connected.json()["username"] == "sweepito"
    assert connected.json()["account_id"] == "1784140"
    assert connected.json()["token_hint"] == "1234"  # noqa: S105
    assert "IGAA-secret" not in connected.text
    assert client.post(f"{CONNECTION}/check").status_code == 200
    assert client.delete(CONNECTION).json()["connected"] is False
    assert client.get(CONNECTION).json()["connected"] is False


def test_instagram_refused_token_is_502_and_malformed_token_is_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kodalo.core.settings.platforms import PlatformConnectionError

    def refuse(token: str, account_id: str) -> dict[str, str]:
        raise PlatformConnectionError("Instagram rejected the token.")

    monkeypatch.setattr("kodalo.core.settings.platforms.instagram._fetch_profile", refuse)

    refused = client.put(CONNECTION, json={"access_token": "IGAA-bad", "account_id": "1784140"})
    malformed = client.put(CONNECTION, json={"access_token": "two words", "account_id": "1784140"})
    bad_id = client.put(CONNECTION, json={"access_token": "IGAA-ok", "account_id": "sweepito"})
    missing_id = client.put(CONNECTION, json={"access_token": "IGAA-ok"})

    assert refused.status_code == 502
    assert (malformed.status_code, bad_id.status_code, missing_id.status_code) == (422, 422, 422)
    assert client.get(CONNECTION).json()["connected"] is False


TUNNEL = "/api/v1/settings/platforms/instagram/tunnel"


def test_cloudflared_is_checked_without_installing_and_installed_on_request(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    found: list[Path | None] = [None]
    monkeypatch.setattr("kodalo.core.tunnel.manager.find_cloudflared", lambda data_dir: found[0])

    def install(data_dir: Path) -> Path:
        installed = Path("cloudflared.exe")
        found[0] = installed
        return installed

    monkeypatch.setattr("kodalo.core.tunnel.manager.ensure_cloudflared", install)

    before = client.get(TUNNEL)
    installed = client.post(TUNNEL)

    assert before.json() == {"installed": False}
    assert (installed.status_code, installed.json()) == (200, {"installed": True})
    assert client.get(TUNNEL).json() == {"installed": True}


def test_a_failed_cloudflared_install_is_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kodalo.core.tunnel import TunnelError

    def fail(data_dir: Path) -> Path:
        raise TunnelError("Could not download cloudflared.")

    monkeypatch.setattr("kodalo.core.tunnel.manager.ensure_cloudflared", fail)

    response = client.post(TUNNEL)

    assert response.status_code == 502
    assert "cloudflared" in response.json()["detail"]
