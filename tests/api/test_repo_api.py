from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kodalo.api import deps
from kodalo.api.main import create_app
from kodalo.core.repo import RepoNotFoundError

READ = "/api/v1/studio/repositories"
SETTINGS = "/api/v1/settings/github"
GITHUB = {
    "repos/o/r": {
        "name": "r",
        "owner": {"login": "o"},
        "description": "A tool",
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
        "topics": ["cli"],
        "private": False,
        "fork": False,
        "archived": False,
        "pushed_at": "2026-10-01T10:00:00Z",
    },
    "repos/o/r/languages": {"Python": 100},
    "repos/o/r/git/trees/main?recursive=1": {"tree": [{"path": "a.py", "type": "blob"}]},
}


def fake_gh(path: str) -> Any:
    if path not in GITHUB:
        raise RepoNotFoundError("GitHub has no such repository.")
    return GITHUB[path]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    client = TestClient(create_app())
    client.get(SETTINGS)  # opens the database
    monkeypatch.setattr(deps._services().repos, "_gh", fake_gh)
    return client


def test_read_store_list_and_get(client: TestClient) -> None:
    response = client.post(READ, json={"source": "o/r"})
    assert response.status_code == 200
    body = response.json()
    assert (body["owner"], body["license"], body["languages"][0]["percent"]) == ("o", "MIT", 100.0)
    assert body["top_level"] == [{"path": "a.py", "type": "file"}]

    assert client.get(READ).json() == [body]
    assert client.get(f"{READ}/{body['id']}").json() == body
    source = client.post("/api/v1/studio/source", json={"source": "o/r"}).json()
    assert source["stored_id"] == body["id"]
    assert client.post(READ, json={"source": "o/r", "refresh": True}).json()["id"] == body["id"]


def test_errors(client: TestClient) -> None:
    assert client.post(READ, json={"source": "o/missing"}).status_code == 404
    assert client.post(READ, json={"source": "nope"}).status_code == 422
    assert client.get(f"{READ}/unknown").status_code == 404


def test_local_folder_needs_details(client: TestClient, tmp_path: Path) -> None:
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")
    client.put(SETTINGS, json={"mode": "local_folder", "local_folder": str(tmp_path)})

    source = client.post("/api/v1/studio/source", json={"source": str(folder)}).json()
    assert source["suggested"]["repo"] == "proj"
    assert source["stored_id"] is None

    assert client.post(READ, json={"source": str(folder)}).status_code == 422
    details = {"owner": "me", "repo": "proj", "license": "MIT", "default_branch": "main"}
    response = client.post(READ, json={"source": str(folder), "details": details})
    assert response.status_code == 200
    assert response.json()["languages"][0]["name"] == "Python"
    assert client.post(READ, json={"source": str(folder)}).status_code == 200
