from pathlib import Path

from fastapi.testclient import TestClient

from kodalo.api.main import create_app

URL = "/api/v1/settings/github"


def test_default_save_and_check(tmp_path: Path) -> None:
    client = TestClient(create_app())
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


def test_invalid(tmp_path: Path) -> None:
    client = TestClient(create_app())
    assert client.put(URL, json={"mode": "ftp"}).status_code == 422
    assert client.put(URL, json={"mode": "local_folder"}).status_code == 422


def test_theme_defaults_to_system_and_saves() -> None:
    client = TestClient(create_app())
    url = "/api/v1/settings/theme"
    assert client.get(url).json() == {"theme": "system"}
    assert client.put(url, json={"theme": "dark"}).json() == {"theme": "dark"}
    assert client.get(url).json() == {"theme": "dark"}
    assert client.put(url, json={"theme": "blue"}).status_code == 422


def test_manifest_limit_is_saved_and_checked() -> None:
    client = TestClient(create_app())
    saved = client.put(URL, json={"mode": "gh_cli", "manifest_limit": 25})
    assert saved.json()["manifest_limit"] == 25
    assert client.put(URL, json={"mode": "gh_cli"}).json()["manifest_limit"] == 25  # kept
    assert client.put(URL, json={"mode": "gh_cli", "manifest_limit": 0}).status_code == 422
    assert client.put(URL, json={"mode": "gh_cli", "manifest_limit": 101}).status_code == 422
