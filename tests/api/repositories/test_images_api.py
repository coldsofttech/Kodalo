from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kodalo.api import deps
from kodalo.api.main import create_app

REPOS = "/api/v1/repositories"
SETTINGS = "/api/v1/settings/github"
PNG = b"\x89PNG\r\n\x1a\n" + b"icon"


@pytest.fixture
def added(tmp_path: Path) -> tuple[TestClient, str]:
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")
    client = TestClient(create_app())
    client.put(SETTINGS, json={"mode": "local_folder", "local_folder": str(tmp_path)})
    details = {"owner": "me", "repo": "proj", "license": "MIT", "default_branch": "main"}
    response = client.post(REPOS, json={"source": str(folder), "details": details})
    return client, response.json()["id"]


def test_images_of_an_unknown_repository_are_404(added: tuple[TestClient, str]) -> None:
    client, _ = added

    for kind in ("social-preview", "icon"):
        assert client.get(f"{REPOS}/missing/{kind}").status_code == 404


def test_a_repository_without_images_has_none_to_serve(added: tuple[TestClient, str]) -> None:
    client, repo_id = added

    body = client.get(f"{REPOS}/{repo_id}").json()

    assert (body["has_social_preview"], body["has_icon"]) == (False, False)
    for kind in ("social-preview", "icon"):
        assert client.get(f"{REPOS}/{repo_id}/{kind}").status_code == 404


def test_the_icon_is_served_with_a_policy_that_runs_nothing(
    added: tuple[TestClient, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, repo_id = added
    icon = tmp_path / "icon.png"
    icon.write_bytes(PNG)
    monkeypatch.setattr(deps._services().repos, "icon", lambda repo: (icon, "image/png"))

    response = client.get(f"{REPOS}/{repo_id}/icon")

    assert response.status_code == 200
    assert response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert "default-src 'none'" in response.headers["content-security-policy"]
