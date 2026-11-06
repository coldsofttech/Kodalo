import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app
from kodalo.core.ai import Probe
from kodalo.core.settings.ai import AiConnectionError
from tests.conftest import MemorySecrets

URL = "/api/v1/settings/ai/connections"
KEY = "sk-test-1234567890abcdef"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def fake(provider: str, base_url: str, api_key: str) -> Probe:
        if api_key == "bad":
            raise AiConnectionError("The provider rejected the API key.")
        return Probe(["m-b", "m-a"], "Connected. 2 models available.")

    monkeypatch.setattr("kodalo.core.ai.service.probe", fake)
    return TestClient(create_app())


def test_lists_every_provider_unsaved(client: TestClient) -> None:
    body = client.get(URL).json()
    assert [c["provider"] for c in body] == [
        "claude_api",
        "claude_code",
        "chatgpt_api",
        "gemini_api",
    ]
    assert not any(c["saved"] for c in body)


def test_save_never_returns_the_key(client: TestClient) -> None:
    response = client.put(f"{URL}/claude_api", json={"api_key": KEY})
    assert response.status_code == 200
    assert KEY not in response.text
    body = response.json()
    assert (body["saved"], body["enabled"], body["has_key"]) == (True, True, True)
    assert body["key_hint"] == KEY[-4:]
    assert MemorySecrets.values == {"ai/claude_api": KEY}
    assert KEY not in client.get(URL).text


def test_save_validation(client: TestClient) -> None:
    assert client.put(f"{URL}/nope", json={}).status_code == 422
    assert client.put(f"{URL}/claude_api", json={"api_key": ""}).status_code == 422
    assert client.put(f"{URL}/claude_api", json={"base_url": "ftp://x"}).status_code == 422
    assert client.put(f"{URL}/claude_code", json={"api_key": KEY}).status_code == 422


def test_test_and_status(client: TestClient) -> None:
    assert client.post(f"{URL}/claude_api/test").status_code == 422  # no key yet
    client.put(f"{URL}/claude_api", json={"api_key": KEY})
    assert client.post(f"{URL}/claude_api/test").json() == {
        "provider": "claude_api",
        "ok": True,
        "detail": "Connected. 2 models available.",
    }
    assert client.get(URL).json()[0]["status"] == "ok"

    client.put(f"{URL}/claude_api", json={"api_key": "bad"})
    assert client.post(f"{URL}/claude_api/test").json()["ok"] is False


def test_default_connection(client: TestClient) -> None:
    assert client.put(f"{URL}/default", json={"provider": "claude_api"}).status_code == 422
    client.put(f"{URL}/claude_api", json={"api_key": KEY})
    response = client.put(f"{URL}/default", json={"provider": "claude_api"})
    assert response.json()["is_default"] is True


def test_remove(client: TestClient) -> None:
    client.put(f"{URL}/claude_api", json={"api_key": KEY})
    assert client.delete(f"{URL}/claude_api").status_code == 204
    assert MemorySecrets.values == {}
    assert client.delete(f"{URL}/claude_api").status_code == 204


def test_models(client: TestClient) -> None:
    assert client.get(f"{URL}/claude_api/models").json() == []
    assert client.post(f"{URL}/claude_api/models/refresh").status_code == 422  # no key yet

    client.put(f"{URL}/claude_api", json={"api_key": KEY})
    refreshed = client.post(f"{URL}/claude_api/models/refresh").json()
    assert [m["name"] for m in refreshed] == ["m-a", "m-b"]

    saved = client.put(
        f"{URL}/claude_api/models/mine",
        json={"max_tokens": 500, "temperature": 0.5, "timeout_s": 30},
    )
    assert saved.json()["source"] == "manual"
    assert client.put(f"{URL}/claude_api/models/mine", json={"temperature": 3}).status_code == 422

    default = client.put(f"{URL}/claude_api/default-model", json={"name": "mine"})
    assert default.json()["is_default"] is True
    assert client.get(URL).json()[0]["default_model"] == "mine"
    missing = client.put(f"{URL}/claude_api/default-model", json={"name": "missing"})
    assert missing.status_code == 404

    assert client.delete(f"{URL}/claude_api/models/mine").status_code == 204
    assert client.delete(f"{URL}/claude_api/models/mine").status_code == 404


def test_refresh_failure_is_a_502(client: TestClient) -> None:
    client.put(f"{URL}/claude_api", json={"api_key": "bad"})
    assert client.post(f"{URL}/claude_api/models/refresh").status_code == 502
