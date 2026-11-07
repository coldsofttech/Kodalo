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
