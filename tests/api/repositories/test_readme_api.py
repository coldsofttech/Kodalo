from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kodalo.api.main import create_app

READ = "/api/v1/studio/repositories"
SETTINGS = "/api/v1/settings/github"
README = """# Proj

Proj tidies things up.

## Features

- **Tidy**: tidy things
- Sweep - sweep things

## Install

```
pip install proj
```

See [the guide](docs/guide.md).
"""


@pytest.fixture
def repo(tmp_path: Path) -> tuple[TestClient, str]:
    folder = tmp_path / "proj"
    (folder / "docs").mkdir(parents=True)
    (folder / "README.md").write_text(README, encoding="utf-8")
    (folder / "docs" / "guide.md").write_text("# Guide\n\n## Commands\n\n- `proj run`\n")
    client = TestClient(create_app())
    client.put(SETTINGS, json={"mode": "local_folder", "local_folder": str(tmp_path)})
    details = {"owner": "me", "repo": "proj", "license": "MIT", "default_branch": "main"}
    info = client.post(READ, json={"source": str(folder), "details": details}).json()
    return client, info["id"]


def test_readme_is_read_saved_and_refreshed(repo: tuple[TestClient, str]) -> None:
    client, repo_id = repo
    url = f"{READ}/{repo_id}/readme"
    assert client.get(url).status_code == 404  # not read yet

    response = client.post(url, json={})
    assert response.status_code == 200
    body = response.json()
    assert body["tagline"] == "Proj tidies things up."
    assert body["installation"][0]["method"] == "pip"
    assert body["installation"][0]["evidence"] == {
        "file": "README.md",
        "quote": "pip install proj",
        "status": "documented",
    }
    assert [c["name"] for c in body["capabilities"]] == ["Tidy", "Sweep", "`proj run`"] or [
        c["name"] for c in body["capabilities"]
    ][:2] == ["Tidy", "Sweep"]
    assert [(d["path"], d["status"]) for d in body["documents"]] == [
        ("README.md", "read"),
        ("docs/guide.md", "read"),
    ]
    assert body["use_cases"] == []
    assert client.get(url).json() == body
    assert client.post(url, json={"refresh": True}).status_code == 200


def test_readme_of_an_unknown_repository_is_404(repo: tuple[TestClient, str]) -> None:
    client, _ = repo
    assert client.post(f"{READ}/missing/readme", json={}).status_code == 404
    assert client.get(f"{READ}/missing/readme").status_code == 404
    for suffix in ("plan", ""):
        assert (
            client.post(f"{READ}/missing/readme/analysis/{suffix}".rstrip("/")).status_code == 404
        )


def test_the_ai_needs_the_readme_and_an_ai_connection(repo: tuple[TestClient, str]) -> None:
    client, repo_id = repo
    base = f"{READ}/{repo_id}/readme/analysis"
    assert client.post(f"{base}/plan").status_code == 404  # the README was not read yet

    client.post(f"{READ}/{repo_id}/readme", json={})
    assert client.post(f"{base}/plan").status_code == 422  # no default AI connection


def test_document_limits_are_settings(repo: tuple[TestClient, str]) -> None:
    client, repo_id = repo
    saved = client.put(SETTINGS, json={"mode": "gh_cli", "document_limit": 1, "document_max_kb": 5})
    assert (saved.json()["document_limit"], saved.json()["document_max_kb"]) == (1, 5)
    client.put(SETTINGS, json={"mode": "local_folder", "local_folder": "."})

    body = client.post(f"{READ}/{repo_id}/readme", json={"refresh": True}).json()
    assert [d["status"] for d in body["documents"]] == ["read", "skipped"]
    assert body["documents"][1]["reason"] == "over the document limit"
    for bad in (0, 51):
        assert (
            client.put(SETTINGS, json={"mode": "gh_cli", "document_limit": bad}).status_code == 422
        )
    assert client.put(SETTINGS, json={"mode": "gh_cli", "document_max_kb": 2001}).status_code == 422
