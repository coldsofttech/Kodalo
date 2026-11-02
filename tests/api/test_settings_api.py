from pathlib import Path

from fastapi.testclient import TestClient

from kodalo.api.main import create_app

URL = "/api/v1/settings/github"


def test_default_save_and_check(tmp_path: Path) -> None:
    client = TestClient(create_app())
    assert client.get(URL).json() == {"mode": "gh_cli", "local_folder": ""}

    saved = client.put(URL, json={"mode": "local_folder", "local_folder": str(tmp_path)})
    assert saved.status_code == 200
    assert client.get(URL).json()["mode"] == "local_folder"

    check = client.post(f"{URL}/check").json()
    assert check == {"mode": "local_folder", "ok": True, "detail": f"Using {tmp_path}."}


def test_invalid(tmp_path: Path) -> None:
    client = TestClient(create_app())
    assert client.put(URL, json={"mode": "ftp"}).status_code == 422
    assert client.put(URL, json={"mode": "local_folder"}).status_code == 422
