"""Check the repository a user picked against the chosen GitHub connectivity mode."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from kodalo.core.github import GitHubSettings
from kodalo.core.studio.errors import StudioInvalidError

# The steps of the studio flow, in order. The first two are built so far.
STEPS: tuple[str, ...] = ("source", "repository", "analyze", "ideas", "post")
MAX_SOURCE = 1024

_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
_REPO = r"[A-Za-z0-9._-]{1,100}?"
_ADDRESS = re.compile(
    rf"^(?:https?://(?:www\.)?github\.com/)?(?P<owner>{_OWNER})/(?P<repo>{_REPO})(?:\.git)?/?$"
)


@dataclass(frozen=True)
class Source:
    """A checked repository source. ``owner`` and ``repo`` are set for a GitHub repository."""

    kind: Literal["local_folder", "github"]
    value: str
    name: str
    owner: str = ""
    repo: str = ""
    is_git: bool = False


def validate_source(settings: GitHubSettings, value: str) -> Source:
    """Return the checked source: a folder in ``local_folder`` mode, else a GitHub repository."""
    value = value.strip()
    if not value:
        raise StudioInvalidError("Enter a repository.")
    if len(value) > MAX_SOURCE:
        raise StudioInvalidError(f"The source must be at most {MAX_SOURCE} characters.")
    if settings.mode == "local_folder":
        return _folder(value)
    return _github(value)


def _folder(value: str) -> Source:
    path = Path(value).expanduser()
    if not path.is_dir():
        raise StudioInvalidError("That folder does not exist.")
    return Source("local_folder", str(path), path.resolve().name, is_git=(path / ".git").exists())


def _github(value: str) -> Source:
    match = _ADDRESS.match(value)
    if match is None:
        raise StudioInvalidError("Use a GitHub address like https://github.com/owner/repo.")
    owner, repo = match["owner"], match["repo"]
    return Source("github", f"https://github.com/{owner}/{repo}", repo, owner, repo)
