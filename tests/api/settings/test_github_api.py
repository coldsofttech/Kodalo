from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

URL = "/api/v1/settings/github"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_default_save_and_check(client: TestClient, tmp_path: Path) -> None:
    assert client.get(URL).json() == {
        "mode": "gh_cli",
        "local_folder": "",
        "manifest_limit": 10,
        "document_limit": 10,
        "document_max_kb": 200,
    }

    saved = client.put(URL, json={"mode": "local_folder", "local_folder": str(tmp_path)})
    assert saved.status_code == 200
    assert client.get(URL).json()["mode"] == "local_folder"

    check = client.post(f"{URL}/check").json()
    assert check == {"mode": "local_folder", "ok": True, "detail": f"Using {tmp_path}."}


def test_saving_returns_what_was_saved(client: TestClient, tmp_path: Path) -> None:
    body = {"mode": "local_folder", "local_folder": str(tmp_path)}
    assert client.put(URL, json=body).json()["local_folder"] == str(tmp_path)
    assert client.put(URL, json={"mode": "web_fetch"}).json() == {
        "mode": "web_fetch",
        "local_folder": str(tmp_path),  # a folder left out is kept
        "manifest_limit": 10,
        "document_limit": 10,
        "document_max_kb": 200,
    }


def test_the_setting_survives_a_new_app(tmp_path: Path) -> None:
    TestClient(create_app()).put(URL, json={"mode": "web_fetch"})
    assert TestClient(create_app()).get(URL).json()["mode"] == "web_fetch"


def test_invalid(client: TestClient) -> None:
    assert client.put(URL, json={"mode": "ftp"}).status_code == 422
    assert client.put(URL, json={"mode": "local_folder"}).status_code == 422
    assert client.put(URL, json={}).status_code == 422
    assert client.put(URL, json={"mode": "gh_cli", "local_folder": "x" * 1025}).status_code == 422


def test_a_rejected_save_keeps_the_saved_setting(client: TestClient) -> None:
    client.put(URL, json={"mode": "web_fetch"})
    assert client.put(URL, json={"mode": "ftp"}).status_code == 422
    assert client.get(URL).json()["mode"] == "web_fetch"


def test_manifest_limit_is_saved_and_checked(client: TestClient) -> None:
    saved = client.put(URL, json={"mode": "gh_cli", "manifest_limit": 25})
    assert saved.json()["manifest_limit"] == 25
    assert client.put(URL, json={"mode": "gh_cli"}).json()["manifest_limit"] == 25  # kept
    assert client.put(URL, json={"mode": "gh_cli", "manifest_limit": 0}).status_code == 422
    assert client.put(URL, json={"mode": "gh_cli", "manifest_limit": 101}).status_code == 422


def test_document_limits_are_saved_and_checked(client: TestClient) -> None:
    saved = client.put(
        URL, json={"mode": "gh_cli", "document_limit": 5, "document_max_kb": 1500}
    ).json()
    assert (saved["document_limit"], saved["document_max_kb"]) == (5, 1500)
    kept = client.put(URL, json={"mode": "gh_cli"}).json()
    assert (kept["document_limit"], kept["document_max_kb"]) == (5, 1500)

    for field, bad in [
        ("document_limit", 0),
        ("document_limit", 51),
        ("document_max_kb", 0),
        ("document_max_kb", 2001),
    ]:
        assert client.put(URL, json={"mode": "gh_cli", field: bad}).status_code == 422


def test_check_reports_a_folder_that_does_not_exist(client: TestClient, tmp_path: Path) -> None:
    missing = tmp_path / "nowhere"
    client.put(URL, json={"mode": "local_folder", "local_folder": str(missing)})
    check = client.post(f"{URL}/check")
    assert check.status_code == 200
    assert check.json()["mode"] == "local_folder"
    assert check.json()["ok"] is False
