"""Read a repository from the GitHub API, through the ``gh`` CLI or plain web requests."""

import base64
import binascii
import json
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from kodalo.core.repositories.errors import RepoError, RepoNotFoundError, RepoReadError
from kodalo.core.repositories.models import Entry, Language, RepoInfo, with_percent

Fetch = Callable[[str], Any]
_TIMEOUT = 20
_API = "https://api.github.com/"
MAX_FILE_BYTES = 200 * 1024


def gh_fetch(path: str) -> Any:
    """Get ``path`` from the GitHub API with the ``gh`` CLI."""
    gh = shutil.which("gh")
    if gh is None:
        raise RepoReadError("The GitHub CLI (gh) is not installed.")
    try:
        result = subprocess.run(  # noqa: S603
            [gh, "api", path], capture_output=True, text=True, timeout=_TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RepoReadError("The GitHub CLI did not respond.") from None
    if result.returncode != 0:
        if "404" in result.stderr or "Not Found" in result.stderr:
            raise RepoNotFoundError("GitHub has no such repository, or you cannot see it.")
        if "auth" in result.stderr.lower() or "401" in result.stderr:
            raise RepoReadError("The GitHub CLI is not signed in. Run: gh auth login")
        raise RepoReadError("The GitHub CLI could not read the repository.")
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise RepoReadError("GitHub sent an answer Kodalo could not read.") from None


def web_fetch(path: str) -> Any:
    """Get ``path`` from the public GitHub API without signing in."""
    request = urllib.request.Request(_API + path, headers={"User-Agent": "kodalo"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RepoNotFoundError("GitHub has no such public repository.") from None
        if error.code in (403, 429):
            raise RepoReadError("GitHub is limiting requests. Try again later.") from None
        raise RepoReadError(f"GitHub answered with status {error.code}.") from None
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        raise RepoReadError("GitHub could not be reached.") from None


def read_github(owner: str, repo: str, fetch: Fetch, method: str) -> RepoInfo:
    """Read the metadata, languages and top-level structure of ``owner/repo``."""
    data = fetch(f"repos/{owner}/{repo}")
    warnings: list[str] = []
    name = str(data.get("name") or repo)
    login = str((data.get("owner") or {}).get("login") or owner)
    branch = data.get("default_branch")

    languages: tuple[Language, ...] = ()
    try:
        sizes = fetch(f"repos/{login}/{name}/languages")
        languages = with_percent({str(k): int(v) for k, v in sizes.items()})
    except RepoReadError:
        warnings.append("The languages could not be read.")

    entries: tuple[Entry, ...] = ()
    paths: tuple[Entry, ...] = ()
    count = 0
    truncated = False
    if branch:
        try:
            tree = fetch(f"repos/{login}/{name}/git/trees/{branch}?recursive=1")
            entries, count, truncated = _structure(tree)
            paths = _paths(tree)
        except RepoReadError:
            warnings.append("The files could not be listed.")
    if truncated:
        warnings.append("The repository is large, so the file list is incomplete.")

    license_info = data.get("license") or {}
    return RepoInfo(
        url=f"https://github.com/{login}/{name}",
        owner=login,
        name=name,
        description=str(data.get("description") or ""),
        homepage=str(data.get("homepage") or ""),
        default_branch=branch,
        license=license_info.get("spdx_id") or license_info.get("name"),
        topics=tuple(str(t) for t in data.get("topics") or ()),
        is_private=bool(data.get("private")),
        is_fork=bool(data.get("fork")),
        is_archived=bool(data.get("archived")),
        last_pushed_at=data.get("pushed_at"),
        languages=languages,
        top_level=entries,
        paths=paths,
        file_count=count,
        access_method=method,
        tree_truncated=truncated,
        warnings=tuple(warnings),
    )


def read_bytes(fetch: Fetch, owner: str, repo: str, path: str, limit: int) -> bytes | None:
    """Return the bytes of one file, or ``None`` when it is over ``limit`` or cannot be read."""
    try:
        data = fetch(f"repos/{owner}/{repo}/contents/{urllib.parse.quote(path)}")
        if not isinstance(data, dict) or int(data.get("size") or 0) > limit:
            return None
        if data.get("encoding") != "base64":
            return None
        return base64.b64decode(str(data.get("content") or ""))
    except (RepoError, ValueError, binascii.Error):
        return None


def read_file(fetch: Fetch, owner: str, repo: str, path: str) -> str | None:
    """Return the text of one file, or ``None`` when it is too large or cannot be read."""
    try:
        data = fetch(f"repos/{owner}/{repo}/contents/{urllib.parse.quote(path)}")
        if not isinstance(data, dict) or int(data.get("size") or 0) > MAX_FILE_BYTES:
            return None
        if data.get("encoding") != "base64":
            return None
        return base64.b64decode(str(data.get("content") or "")).decode("utf-8", errors="replace")
    except (RepoError, ValueError, binascii.Error):
        return None


def _paths(tree: dict[str, Any]) -> tuple[Entry, ...]:
    return tuple(
        Entry(item["path"], "dir" if item["type"] == "tree" else "file")
        for item in tree.get("tree") or []
        if item["type"] in ("tree", "blob")
    )


def _structure(tree: dict[str, Any]) -> tuple[tuple[Entry, ...], int, bool]:
    items = tree.get("tree") or []
    top = [
        Entry(item["path"], "dir" if item["type"] == "tree" else "file")
        for item in items
        if "/" not in item["path"] and item["type"] in ("tree", "blob")
    ]
    top.sort(key=lambda e: (e.type != "dir", e.path.lower()))
    files = sum(1 for item in items if item["type"] == "blob")
    return tuple(top), files, bool(tree.get("truncated"))
