import subprocess
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.settings.github import (
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
    monkeypatch.setattr("kodalo.core.settings.github.service.shutil.which", lambda _: None)
    result = check_connection(GitHubSettings("gh_cli"))
    assert not result.ok
    assert "not installed" in result.detail


def test_the_limits_default_and_are_kept_when_left_out(connectivity: GitHubConnectivity) -> None:
    defaults = connectivity.get()
    assert (defaults.manifest_limit, defaults.document_limit, defaults.document_max_kb) == (
        10,
        10,
        200,
    )
    connectivity.save("gh_cli", None, 25, 5, 1500)
    kept = connectivity.save("web_fetch")
    assert (kept.manifest_limit, kept.document_limit, kept.document_max_kb) == (25, 5, 1500)
    assert connectivity.get() == kept


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        ((0, None, None), "project files"),
        ((101, None, None), "project files"),
        ((None, 0, None), "documents"),
        ((None, 51, None), "documents"),
        ((None, None, 0), "size to read"),
        ((None, None, 2001), "size to read"),
    ],
)
def test_limits_out_of_range_are_refused(
    connectivity: GitHubConnectivity,
    limits: tuple[int | None, int | None, int | None],
    message: str,
) -> None:
    connectivity.save("gh_cli", None, 20, 20, 20)
    with pytest.raises(GitHubInvalidError, match=message):
        connectivity.save("gh_cli", None, *limits)
    kept = connectivity.get()
    assert (kept.manifest_limit, kept.document_limit, kept.document_max_kb) == (20, 20, 20)


def test_the_setting_survives_reopening(tmp_path: Path) -> None:
    first = Database.open(database_path(tmp_path))
    GitHubConnectivity(first).save("web_fetch", None, 30)
    first.close()
    second = Database.open(database_path(tmp_path))
    try:
        saved = GitHubConnectivity(second).get()
    finally:
        second.close()
    assert (saved.mode, saved.manifest_limit) == ("web_fetch", 30)


class _Done:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


SERVICE = "kodalo.core.settings.github.service"


def test_check_gh_signed_in_and_not(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{SERVICE}.shutil.which", lambda _: "gh")
    monkeypatch.setattr(f"{SERVICE}.subprocess.run", lambda *_a, **_k: _Done(0))
    signed_in = check_connection(GitHubSettings("gh_cli"))
    assert signed_in.ok
    assert "signed in" in signed_in.detail

    monkeypatch.setattr(f"{SERVICE}.subprocess.run", lambda *_a, **_k: _Done(1))
    signed_out = check_connection(GitHubSettings("gh_cli"))
    assert not signed_out.ok
    assert "gh auth login" in signed_out.detail


@pytest.mark.parametrize("error", [OSError("no"), subprocess.TimeoutExpired("gh", 1)])
def test_check_gh_that_does_not_respond(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    monkeypatch.setattr(f"{SERVICE}.shutil.which", lambda _: "gh")

    def run(*_a: object, **_k: object) -> None:
        raise error

    monkeypatch.setattr(f"{SERVICE}.subprocess.run", run)
    result = check_connection(GitHubSettings("gh_cli"))
    assert not result.ok
    assert "did not respond" in result.detail


class _Open:
    def __enter__(self) -> "_Open":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_check_web(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: _Open())
    reachable = check_connection(GitHubSettings("web_fetch"))
    assert reachable.ok
    assert "public repositories only" in reachable.detail


def test_check_web_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def limited(*_a: object, **_k: object) -> None:
        raise urllib.error.HTTPError("https://api.github.com", 403, "no", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", limited)
    assert "status 403" in check_connection(GitHubSettings("web_fetch")).detail

    def down(*_a: object, **_k: object) -> None:
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    result = check_connection(GitHubSettings("web_fetch"))
    assert not result.ok
    assert "could not be reached" in result.detail
