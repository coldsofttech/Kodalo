from pathlib import Path

from fastapi.testclient import TestClient

from kodalo.api.main import create_app

URL = "/api/v1/studio/source"


def test_github_and_folder_modes(tmp_path: Path) -> None:
    client = TestClient(create_app())
    ok = client.post(URL, json={"source": "owner/repo"})
    assert ok.status_code == 200
    assert ok.json()["next_step"] == "repository"
    assert client.post(URL, json={"source": "nope"}).status_code == 422

    client.put("/api/v1/settings/github", json={"mode": "local_folder", "local_folder": "x"})
    assert client.post(URL, json={"source": str(tmp_path)}).json()["kind"] == "local_folder"
    assert client.post(URL, json={"source": "owner/repo"}).status_code == 422
