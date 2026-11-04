"""Reading project files while reading a repository."""

import base64
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.github import GitHubConnectivity, GitHubInvalidError, GitHubSettings
from kodalo.core.repo import LocalDetails, RepoNotFoundError, RepoService
from kodalo.core.storage import Database, database_path
from kodalo.core.studio import validate_source


def _file(text: str, size: int | None = None) -> dict[str, Any]:
    return {
        "size": len(text) if size is None else size,
        "encoding": "base64",
        "content": base64.b64encode(text.encode()).decode(),
    }


def _api(files: dict[str, dict[str, Any]]) -> dict[str, Any]:
    tree = [{"path": path, "type": "blob"} for path in files]
    data: dict[str, Any] = {
        "repos/o/r": {"name": "r", "owner": {"login": "o"}, "default_branch": "main"},
        "repos/o/r/languages": {},
        "repos/o/r/git/trees/main?recursive=1": {"tree": tree},
    }
    data |= {f"repos/o/r/contents/{path}": body for path, body in files.items()}
    return data


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


def _read(service: RepoService, limit: int = 10) -> Any:
    settings = GitHubSettings(mode="gh_cli", manifest_limit=limit)
    return service.read(settings, validate_source(settings, "o/r"))


def test_github_manifests_are_read_and_stored(database: Database) -> None:
    api = FakeApi(
        _api(
            {
                "package.json": _file('{"name": "web", "dependencies": {"react": "1"}}'),
                "package-lock.json": _file("{}"),
            }
        )
    )
    service = RepoService(database, gh=api)

    info = _read(service)

    (project,) = [m for m in info.manifests if not m.is_lockfile]
    assert (project.package_name, project.dependencies) == ("web", ("react",))
    assert "repos/o/r/contents/package-lock.json" not in api.calls  # lockfiles are never opened
    assert service.get(info.id).manifests == info.manifests  # kept in the database


def test_limit_reads_top_folders_first_and_says_so(database: Database) -> None:
    files = {
        "pkg/b/package.json": _file('{"name": "deep"}'),
        "package.json": _file('{"name": "root"}'),
        "pkg/package.json": _file('{"name": "mid"}'),
    }
    api = FakeApi(_api(files))

    info = _read(RepoService(database, gh=api), limit=2)

    names = {m.path: m.package_name for m in info.manifests}
    assert names == {"package.json": "root", "pkg/package.json": "mid", "pkg/b/package.json": None}
    assert any("Only 2 of 3 project files were read" in w for w in info.warnings)
    assert "repos/o/r/contents/pkg/b/package.json" not in api.calls


def test_unreadable_and_oversized_files_keep_the_entry_with_a_warning(database: Database) -> None:
    api = FakeApi(_api({"package.json": _file("{}", size=300_000)}))

    info = _read(RepoService(database, gh=api))

    assert [m.package_name for m in info.manifests] == [None]
    assert any("could not be read" in w for w in info.warnings)


def test_user_parser_config_teaches_a_new_stack(database: Database, tmp_path: Path) -> None:
    parsers = tmp_path / "parsers"
    parsers.mkdir()
    config = {
        "schema_version": 1,
        "id": "my-stack",
        "ecosystem": "mystack",
        "files": ["stack.json"],
        "format": "json",
        "name": ["name"],
        "dependencies": [{"path": "deps", "shape": "keys"}],
    }
    (parsers / "stack.json").write_text(json.dumps(config), encoding="utf-8")
    api = FakeApi(_api({"stack.json": _file('{"name": "n", "deps": {"a": 1}}')}))

    info = _read(RepoService(database, gh=api, parsers_dir=parsers))

    (manifest,) = info.manifests
    assert (manifest.ecosystem, manifest.package_name, manifest.dependencies) == (
        "mystack",
        "n",
        ("a",),
    )


def test_local_folder_reads_every_manifest_ignoring_the_limit(
    database: Database, tmp_path: Path
) -> None:
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "pyproject.toml").write_text('[project]\nname = "p"\n', encoding="utf-8")
    (folder / "web").mkdir()
    (folder / "web" / "package.json").write_text('{"name": "w"}', encoding="utf-8")
    settings = GitHubSettings(mode="local_folder", local_folder=str(tmp_path), manifest_limit=1)
    details = LocalDetails(owner="o", repo="r", license="MIT", default_branch="main")

    info = RepoService(database).read(settings, validate_source(settings, str(folder)), details)

    assert {m.path: m.package_name for m in info.manifests} == {
        "pyproject.toml": "p",
        "web/package.json": "w",
    }


def test_manifest_limit_setting(database: Database) -> None:
    connectivity = GitHubConnectivity(database)

    assert connectivity.get().manifest_limit == 10
    assert connectivity.save("gh_cli", manifest_limit=25).manifest_limit == 25
    assert connectivity.save("web_fetch").manifest_limit == 25  # kept
    for bad in (0, 101):
        with pytest.raises(GitHubInvalidError):
            connectivity.save("gh_cli", manifest_limit=bad)
