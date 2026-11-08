import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app
from kodalo.core.ai import Probe
from kodalo.core.settings.ai import AiConnectionError

AI = "/api/v1/settings/ai"
KEY = "sk-test-1234567890abcdef"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def fake(provider: str, base_url: str, api_key: str) -> Probe:
        if api_key == "bad":
            raise AiConnectionError("The provider rejected the API key.")
        return Probe(["m-a"], "Connected. 1 models available.")

    monkeypatch.setattr("kodalo.core.ai.service.probe", fake)
    return TestClient(create_app())


def _test_connection(client: TestClient, key: str = KEY) -> None:
    client.put(f"{AI}/connections/claude_api", json={"api_key": key})
    client.post(f"{AI}/connections/claude_api/test")


def test_settings_default_and_change(client: TestClient) -> None:
    assert client.get(f"{AI}/history/settings").json() == {
        "store_text": False,
        "retention_days": 90,
    }
    changed = client.put(
        f"{AI}/history/settings", json={"store_text": True, "retention_days": 30}
    ).json()
    assert changed == {"store_text": True, "retention_days": 30}
    kept = client.put(f"{AI}/history/settings", json={"retention_days": 0}).json()
    assert kept == {"store_text": True, "retention_days": 0}
    assert client.put(f"{AI}/history/settings", json={"retention_days": -1}).status_code == 422


def test_connection_tests_are_listed_with_usage(client: TestClient) -> None:
    _test_connection(client)
    page = client.get(f"{AI}/history").json()
    assert page["total"] == 1
    entry = page["items"][0]
    assert (entry["purpose"], entry["status"], entry["provider"]) == (
        "connection_test",
        "ok",
        "claude_api",
    )
    usage = client.get(f"{AI}/usage").json()
    assert usage["calls"] == 1
    assert usage["rows"][0]["provider"] == "claude_api"
    assert len(usage["days"]) == 1


def test_failed_connection_test_is_recorded(client: TestClient) -> None:
    _test_connection(client, "bad")
    entry = client.get(f"{AI}/history").json()["items"][0]
    assert entry["status"] == "failed"
    assert entry["error"] == "The provider rejected the API key."


def test_one_entry_and_missing_entry(client: TestClient) -> None:
    _test_connection(client)
    call_id = client.get(f"{AI}/history").json()["items"][0]["id"]
    detail = client.get(f"{AI}/history/{call_id}").json()
    assert detail["prompt_text"] is None
    assert detail["has_text"] is False
    assert client.get(f"{AI}/history/nope").status_code == 404


def test_filters_and_invalid_periods(client: TestClient) -> None:
    _test_connection(client)
    assert client.get(f"{AI}/history", params={"period": "day"}).json()["total"] == 1
    custom = {"period": "custom", "start": "2000-01-01", "end": "2000-01-02"}
    assert client.get(f"{AI}/history", params=custom).json()["total"] == 0
    assert client.get(f"{AI}/usage", params=custom).json()["rows"] == []
    assert client.get(f"{AI}/history", params={"period": "custom"}).status_code == 422
    assert client.get(f"{AI}/history", params={"period": "decade"}).status_code == 422
    bad = {"period": "custom", "start": "yesterday"}
    assert client.get(f"{AI}/usage", params=bad).status_code == 422
    assert client.get(f"{AI}/history", params={"limit": 0}).status_code == 422


def test_purge_removes_everything(client: TestClient) -> None:
    _test_connection(client)
    assert client.delete(f"{AI}/history").json() == {"deleted": 1}
    assert client.get(f"{AI}/history").json()["total"] == 0
