from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.github import (
    DEFAULT_MODE,
    GitHubConnectivity,
    GitHubInvalidError,
    GitHubSettings,
    check_connection,
)
from kodalo.core.storage import Database, database_path


@pytest.fixture
def connectivity(tmp_path: Path) -> Iterator[GitHubConnectivity]:
    database = Database.open(database_path(tmp_path))
    yield GitHubConnectivity(database)
    database.close()


def test_defaults_to_gh_cli(connectivity: GitHubConnectivity) -> None:
    assert connectivity.get() == GitHubSettings(mode="gh_cli", local_folder="")
    assert DEFAULT_MODE == "gh_cli"


def test_save_and_replace(connectivity: GitHubConnectivity, tmp_path: Path) -> None:
    connectivity.save("local_folder", str(tmp_path))
    assert connectivity.get() == GitHubSettings("local_folder", str(tmp_path))
    connectivity.save("web_fetch")
    assert connectivity.get() == GitHubSettings("web_fetch", str(tmp_path))


def test_invalid_values(connectivity: GitHubConnectivity) -> None:
    with pytest.raises(GitHubInvalidError, match="Unknown mode"):
        connectivity.save("ftp")
    with pytest.raises(GitHubInvalidError, match="needs a folder"):
        connectivity.save("local_folder")
    with pytest.raises(GitHubInvalidError, match="at most"):
        connectivity.save("gh_cli", "x" * 2000)


def test_check_local_folder(tmp_path: Path) -> None:
    assert check_connection(GitHubSettings("local_folder", str(tmp_path))).ok
    assert not check_connection(GitHubSettings("local_folder", str(tmp_path / "no"))).ok
    assert not check_connection(GitHubSettings("local_folder", "")).ok


def test_check_gh_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("kodalo.core.github.service.shutil.which", lambda _: None)
    result = check_connection(GitHubSettings("gh_cli"))
    assert not result.ok
    assert "not installed" in result.detail
