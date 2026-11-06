from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.repo import (
    LocalDetails,
    RepoDetailsError,
    RepoNotFoundError,
    RepoReadError,
    RepoService,
    suggest,
)
from kodalo.core.settings.github import GitHubSettings
from kodalo.core.storage import Database, database_path
from kodalo.core.studio import validate_source

API = {
    "repos/o/r": {
        "name": "r",
        "owner": {"login": "o"},
        "description": "A tool",
        "homepage": "https://r.dev",
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
        "topics": ["cli", "python"],
        "private": False,
        "fork": True,
        "archived": False,
        "pushed_at": "2026-10-01T10:00:00Z",
    },
    "repos/o/r/languages": {"Python": 750, "Shell": 250},
    "repos/o/r/git/trees/main?recursive=1": {
        "truncated": False,
        "tree": [
            {"path": "src", "type": "tree"},
            {"path": "src/a.py", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ],
    },
}


class FakeApi:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.calls: list[str] = []

    def __call__(self, path: str) -> Any:
        self.calls.append(path)
        if path not in self.data:
            raise RepoNotFoundError("missing")
        return self.data[path]


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path / "data"))
    yield db
    db.close()


def test_github_read_is_stored_and_reused(database: Database) -> None:
    api = FakeApi(API)
    service = RepoService(database, gh=api)
    settings = GitHubSettings("gh_cli")
    source = validate_source(settings, "o/r")

    info = service.read(settings, source)

    assert (info.owner, info.name, info.license, info.default_branch) == ("o", "r", "MIT", "main")
    assert info.topics == ("cli", "python")
    assert info.is_fork
    assert not info.is_private
    assert [(x.name, x.bytes, x.percent) for x in info.languages] == [
        ("Python", 750, 75.0),
        ("Shell", 250, 25.0),
    ]
    assert [(e.path, e.type) for e in info.top_level] == [("src", "dir"), ("README.md", "file")]
    assert info.file_count == 2
    assert info.access_method == "gh_cli"
    assert info.last_scanned_at

    calls = len(api.calls)
    again = service.read(settings, source)
    assert again == info
    assert len(api.calls) == calls
    service.read(settings, source, refresh=True)
    assert len(api.calls) == calls * 2
    assert len(service.list_repos()) == 1
    assert service.get(info.id).name == "r"


def test_web_mode_uses_the_web_fetcher(database: Database) -> None:
    web = FakeApi(API)
    service = RepoService(database, gh=FakeApi({}), web=web)
    settings = GitHubSettings("web_fetch")
    info = service.read(settings, validate_source(settings, "o/r"))
    assert info.access_method == "web_fetch"
    assert web.calls


def test_missing_parts_become_warnings(database: Database) -> None:
    service = RepoService(database, gh=FakeApi({"repos/o/r": API["repos/o/r"]}))
    settings = GitHubSettings("gh_cli")
    info = service.read(settings, validate_source(settings, "o/r"))
    assert info.languages == ()
    assert len(info.warnings) == 2


def test_not_found_and_unknown_id(database: Database) -> None:
    service = RepoService(database, gh=FakeApi({}))
    settings = GitHubSettings("gh_cli")
    with pytest.raises(RepoNotFoundError):
        service.read(settings, validate_source(settings, "o/r"))
    with pytest.raises(RepoNotFoundError):
        service.get("nope")
    assert issubclass(RepoNotFoundError, RepoReadError)


def test_local_folder(database: Database, tmp_path: Path) -> None:
    folder = tmp_path / "proj"
    (folder / "src").mkdir(parents=True)
    (folder / "node_modules").mkdir()
    (folder / "src" / "a.py").write_text("x" * 30)
    (folder / "b.js").write_text("y" * 10)
    (folder / "node_modules" / "skip.js").write_text("z" * 999)
    service = RepoService(database)
    settings = GitHubSettings("local_folder", str(tmp_path))
    source = validate_source(settings, str(folder))

    with pytest.raises(RepoDetailsError, match="owner"):
        service.read(settings, source)

    details = LocalDetails(owner="me", repo="proj", license="MIT", default_branch="main")
    info = service.read(settings, source, details)
    assert info.url == "https://github.com/me/proj"
    assert info.local_path == str(folder)
    assert [(x.name, x.bytes) for x in info.languages] == [("Python", 30), ("JavaScript", 10)]
    assert info.file_count == 2
    assert info.access_method == "local_folder"

    # Stored, so a later read needs no details; a refresh reuses the stored ones.
    assert service.read(settings, source).id == info.id
    assert service.read(settings, source, refresh=True).license == "MIT"


def test_suggest_falls_back_to_the_folder_name(tmp_path: Path) -> None:
    folder = tmp_path / "plain"
    folder.mkdir()
    assert suggest(folder).repo == "plain"
