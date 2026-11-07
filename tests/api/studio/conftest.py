from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from kodalo.api import deps
from kodalo.api.main import create_app

READ = "/api/v1/studio/repositories"


@dataclass
class Studio:
    """A client with one repository and one brand to make posts for."""

    client: TestClient
    repo_id: str
    brand_id: str

    @property
    def url(self) -> str:
        return f"{READ}/{self.repo_id}"

    def ask(self, **extra: str) -> dict[str, str]:
        """The body (or query) that names one idea of a tool post."""
        return {"brand_id": self.brand_id, "post_type": "tool", "idea_id": "idea-1", **extra}


@pytest.fixture
def studio(tmp_path: Path) -> Studio:
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")
    client = TestClient(create_app())
    client.put(
        "/api/v1/settings/github", json={"mode": "local_folder", "local_folder": str(tmp_path)}
    )
    details = {"owner": "me", "repo": "proj", "license": "MIT", "default_branch": "main"}
    repo = client.post(READ, json={"source": str(folder), "details": details}).json()
    brand = client.post(
        "/api/v1/brands", json={"name": "Acme", "palette": "system-midnight"}
    ).json()
    return Studio(client, repo["id"], brand["id"])


@pytest.fixture
def services(studio: Studio) -> deps.Services:
    return deps._services()


@pytest.fixture
def custom_canvas(monkeypatch: pytest.MonkeyPatch, services: deps.Services) -> None:
    """Make every brand look as if its canvas was made for the custom platform."""
    canvas = SimpleNamespace(platform_id="custom", width=100, height=100)
    monkeypatch.setattr(services.brands, "get", lambda brand_id: SimpleNamespace(canvas=canvas))


@pytest.fixture
def unsupported_canvas(monkeypatch: pytest.MonkeyPatch, services: deps.Services) -> None:
    """Make every brand look as if its canvas was made for a platform with no skill files."""
    canvas = SimpleNamespace(platform_id="tiktok", width=100, height=100)
    monkeypatch.setattr(services.brands, "get", lambda brand_id: SimpleNamespace(canvas=canvas))
