import base64
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kodalo.api import deps
from kodalo.api.main import create_app
from kodalo.core.repositories import RepoNotFoundError

READ = "/api/v1/studio/repositories"
SETTINGS = "/api/v1/settings/github"
PYPROJECT = b'[project]\nname = "r"\nversion = "1.2.3"\ndependencies = ["typer>=0.9"]\n'
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
    "repos/o/r/contents/pyproject.toml": {
        "size": 60,
        "encoding": "base64",
        "content": base64.b64encode(PYPROJECT).decode(),
    },
    "repos/o/r/git/trees/main?recursive=1": {
        "tree": [
            {"path": "a.py", "type": "blob"},
            {"path": "tests", "type": "tree"},
            {"path": "pyproject.toml", "type": "blob"},
            {"path": "turbo.json", "type": "blob"},
        ]
    },
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
    assert body["top_level"][0] == {"path": "tests", "type": "dir"}
    assert body["notable_dirs"] == [{"path": "tests", "purpose": "tests"}]
    assert body["manifests"] == [
        {
            "path": "pyproject.toml",
            "ecosystem": "python",
            "is_lockfile": False,
            "package_name": "r",
            "version": "1.2.3",
            "dependencies": ["typer"],
            "dev_dependencies": [],
            "evidence": 'name = "r"',
        }
    ]
    assert body["documentation"]["readmes"] == []
    assert body["skipped"] == []
    assert body["is_monorepo"] is True
    assert body["monorepo_signals"] == ["turbo.json"]

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


def test_frameworks_are_returned_with_evidence(client: TestClient) -> None:
    body = client.post(READ, json={"source": "o/r"}).json()
    assert body["frameworks"] == [
        {
            "id": "typer",
            "name": "Typer",
            "category": "cli",
            "evidence": 'pyproject.toml: "typer"',
            "path": "pyproject.toml",
        }
    ]


def test_ai_analysis_with_nothing_to_ask_or_nothing_stored(client: TestClient) -> None:
    repo_id = client.post(READ, json={"source": "o/r"}).json()["id"]
    plan = client.post(f"{READ}/{repo_id}/analysis/plan")
    assert plan.status_code == 200
    assert plan.json()["dependencies"] == []  # every package is already understood
    result = client.post(f"{READ}/{repo_id}/analysis")
    assert result.status_code == 200
    assert result.json()["frameworks"] == []
    for suffix in ("analysis/plan", "analysis"):
        assert client.post(f"{READ}/missing/{suffix}").status_code == 404


def test_tooling_is_returned_and_the_plan_lists_tool_files(client: TestClient) -> None:
    body = client.post(READ, json={"source": "o/r"}).json()
    assert isinstance(body["tooling"], list)
    plan = client.post(f"{READ}/{body['id']}/analysis/plan").json()
    assert isinstance(plan["tool_files"], list)


def test_repositories_add_list_get_and_remove(client: TestClient) -> None:
    assert client.get("/api/v1/repositories").json() == []
    added = client.post("/api/v1/repositories", json={"source": "o/r"})
    assert added.status_code == 201
    repo_id = added.json()["id"]

    assert [r["id"] for r in client.get("/api/v1/repositories").json()] == [repo_id]
    assert client.get(f"/api/v1/repositories/{repo_id}").json()["owner"] == "o"
    checked = client.post("/api/v1/repositories/check", json={"source": "o/r"})
    assert checked.json()["stored_id"] == repo_id
    assert client.post("/api/v1/repositories/check", json={"source": "nonsense"}).status_code == 422

    assert client.delete(f"/api/v1/repositories/{repo_id}").status_code == 204
    assert client.get("/api/v1/repositories").json() == []
    assert client.get(f"/api/v1/repositories/{repo_id}").status_code == 404
    assert client.delete(f"/api/v1/repositories/{repo_id}").status_code == 404


def test_social_preview_is_saved_served_and_removed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"data"
    repos = deps._services().repos
    added = client.post("/api/v1/repositories", json={"source": "o/r"}).json()
    assert added["has_social_preview"] is False
    assert client.get(f"/api/v1/repositories/{added['id']}/social-preview").status_code == 404

    monkeypatch.setattr(repos, "_preview", lambda owner, repo: png)
    refreshed = client.post("/api/v1/repositories", json={"source": "o/r", "refresh": True})
    assert refreshed.json()["has_social_preview"] is True
    image = client.get(f"/api/v1/repositories/{added['id']}/social-preview")
    assert (image.status_code, image.headers["content-type"], image.content) == (
        200,
        "image/png",
        png,
    )

    monkeypatch.setattr(repos, "_preview", lambda owner, repo: b"not an image")
    again = client.post("/api/v1/repositories", json={"source": "o/r", "refresh": True})
    assert again.json()["has_social_preview"] is False  # an image that is gone is dropped

    monkeypatch.setattr(repos, "_preview", lambda owner, repo: png)
    client.post("/api/v1/repositories", json={"source": "o/r", "refresh": True})
    assert client.delete(f"/api/v1/repositories/{added['id']}").status_code == 204
    assert repos.social_preview(added["id"]) is None
