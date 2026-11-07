"""The repository icon: the candidates, and keeping the one the README analysis with AI picked."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.repositories import ReadmeAssistant, ReadmeService, RepoService
from kodalo.core.repositories.icon import icon_candidates, icon_type
from kodalo.core.repositories.models import Entry
from kodalo.core.settings.github import GitHubSettings
from kodalo.core.storage import Database, database_path
from kodalo.core.studio import validate_source
from tests.core.repositories.test_readme import README, FakeApi, _Ai, _api

SVG = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
SETTINGS = GitHubSettings("gh_cli")


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path / "data"))
    yield db
    db.close()


def _entries(*paths: str) -> list[Entry]:
    return [Entry(path, "file") for path in paths]


def test_candidates_are_images_named_like_an_icon_best_first() -> None:
    found = icon_candidates(
        _entries(
            "docs/images/logo.png",
            "logo.svg",
            "assets/icon.png",
            "node_modules/x/logo.svg",
            "docs/screenshot.png",
            "src/icon.py",
            "assets/logo-long-name.svg",
        )
    )

    assert found == (
        "logo.svg",
        "assets/logo-long-name.svg",
        "assets/icon.png",
        "docs/images/logo.png",
    )


def test_the_image_type_comes_from_the_first_bytes() -> None:
    assert icon_type(b"\x89PNG\r\n\x1a\nxx") == "png"
    assert icon_type(b"\xff\xd8\xffxx") == "jpg"
    assert icon_type(b"RIFF1234WEBPxx") == "webp"
    assert icon_type(SVG.encode()) == "svg"
    assert icon_type(b"<html></html>") is None


def _assistant(
    database: Database, tmp_path: Path, reply: dict[str, object]
) -> tuple[ReadmeAssistant, RepoService, str]:
    files = {"README.md": README, "assets/icon.svg": SVG, "docs/screenshot.png": "x"}
    repos = RepoService(database, gh=FakeApi(_api(files)), icons_dir=tmp_path / "icons")
    info = repos.read(SETTINGS, validate_source(SETTINGS, "o/r"))
    service = ReadmeService(database, repos)
    service.read(SETTINGS, info.id)
    return ReadmeAssistant(service, _Ai(json.dumps(reply))), repos, info.id  # type: ignore[arg-type]


def test_the_picked_icon_is_kept(database: Database, tmp_path: Path) -> None:
    assistant, repos, repo_id = _assistant(
        database, tmp_path, {"purpose": {"summary": "s"}, "icon": {"path": "assets/icon.svg"}}
    )
    assert repos.get(repo_id).icon_candidates == ("assets/icon.svg",)

    result = assistant.apply(SETTINGS, repo_id)

    info = repos.get(repo_id)
    assert result.icon == "assets/icon.svg"
    assert (info.has_icon, info.icon_path) == (True, "assets/icon.svg")
    assert info.icon_checked_at is not None
    found = repos.icon(repo_id)
    assert found is not None
    assert found[1] == "image/svg+xml"
    assert found[0].read_text() == SVG


def test_no_icon_is_marked_as_looked_at(database: Database, tmp_path: Path) -> None:
    assistant, repos, repo_id = _assistant(
        database, tmp_path, {"purpose": {"summary": "s"}, "icon": {"path": ""}}
    )

    result = assistant.apply(SETTINGS, repo_id)

    info = repos.get(repo_id)
    assert result.icon == ""
    assert (info.has_icon, info.icon_path) == (False, "")
    assert info.icon_checked_at is not None


def test_a_path_that_is_not_a_candidate_is_not_kept(database: Database, tmp_path: Path) -> None:
    assistant, repos, repo_id = _assistant(
        database, tmp_path, {"purpose": {"summary": "s"}, "icon": {"path": "docs/screenshot.png"}}
    )

    assistant.apply(SETTINGS, repo_id)

    assert repos.get(repo_id).has_icon is False


def test_a_later_answer_without_an_icon_removes_the_old_one(
    database: Database, tmp_path: Path
) -> None:
    assistant, repos, repo_id = _assistant(
        database, tmp_path, {"purpose": {"summary": "s"}, "icon": {"path": "assets/icon.svg"}}
    )
    assistant.apply(SETTINGS, repo_id)

    repos.save_icon(repo_id, "", None)

    assert repos.get(repo_id).has_icon is False
    assert repos.icon(repo_id) is None
