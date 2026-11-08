from pathlib import Path

import pytest

from kodalo.core.settings.github import GitHubSettings
from kodalo.core.studio import StudioInvalidError, validate_source

CLI = GitHubSettings("gh_cli")


@pytest.mark.parametrize(
    "value",
    ["owner/repo", "https://github.com/owner/repo", "https://github.com/owner/repo.git/"],
)
def test_github_addresses(value: str) -> None:
    source = validate_source(CLI, value)
    assert (source.kind, source.owner, source.repo) == ("github", "owner", "repo")
    assert source.value == "https://github.com/owner/repo"


@pytest.mark.parametrize("value", ["", "  ", "nonsense", "https://example.com/o/r", "a/b/c"])
def test_invalid_github(value: str) -> None:
    with pytest.raises(StudioInvalidError):
        validate_source(GitHubSettings("web_fetch"), value)


def test_too_long() -> None:
    with pytest.raises(StudioInvalidError, match="at most"):
        validate_source(CLI, "a/" + "b" * 2000)


def test_folder(tmp_path: Path) -> None:
    settings = GitHubSettings("local_folder", str(tmp_path))
    plain = validate_source(settings, str(tmp_path))
    assert (plain.kind, plain.is_git, plain.name) == ("local_folder", False, tmp_path.name)
    (tmp_path / ".git").mkdir()
    assert validate_source(settings, str(tmp_path)).is_git
    with pytest.raises(StudioInvalidError, match="does not exist"):
        validate_source(settings, str(tmp_path / "missing"))
