"""Read a repository from a folder on this computer, using git and the files themselves."""

import contextlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kodalo.core.repo.errors import RepoDetailsError
from kodalo.core.repo.models import Entry, LocalDetails, RepoInfo, with_percent

MAX_FILES = 50_000
MAX_TOP_LEVEL = 200
_SKIP_DIRS = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target"}
    | {".tox", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".idea", ".vscode"}
)
_LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".swift": "Swift",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".lua": "Lua",
    ".dart": "Dart",
    ".nsi": "NSIS",
    ".nsh": "NSIS",
}
_REMOTE = re.compile(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$")
_TIMEOUT = 10


@dataclass(frozen=True)
class Suggestion:
    """Values git can offer to prefill the details form."""

    owner: str = ""
    repo: str = ""
    default_branch: str = ""


def _git(folder: Path, *args: str) -> str:
    git = shutil.which("git")
    if git is None:
        return ""
    try:
        result = subprocess.run(  # noqa: S603
            [git, "-C", str(folder), *args],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def suggest(folder: Path) -> Suggestion:
    """Guess the owner, repository name and branch of ``folder`` from git, or from its name."""
    match = _REMOTE.search(_git(folder, "remote", "get-url", "origin"))
    branch = _git(folder, "rev-parse", "--abbrev-ref", "HEAD")
    return Suggestion(
        owner=match["owner"] if match else "",
        repo=match["repo"] if match else folder.resolve().name,
        default_branch="" if branch in ("", "HEAD") else branch,
    )


def read_local(folder: Path, details: LocalDetails) -> RepoInfo:
    """Read ``folder``. The owner, repository, license and branch must be in ``details``."""
    missing = [
        label
        for label, value in (
            ("owner", details.owner),
            ("repository name", details.repo),
            ("license", details.license),
            ("default branch", details.default_branch),
        )
        if not value.strip()
    ]
    if missing:
        raise RepoDetailsError(f"Please fill in: {', '.join(missing)}.")
    sizes: dict[str, int] = {}
    count, truncated = _walk(folder, sizes)
    warnings = ["Read from a folder, so private, fork and archived come from your answers."]
    if truncated:
        warnings.append("The folder is large, so the file list is incomplete.")
    owner, repo = details.owner.strip(), details.repo.strip()
    return RepoInfo(
        url=f"https://github.com/{owner}/{repo}",
        owner=owner,
        name=repo,
        description=details.description.strip(),
        homepage=details.homepage.strip(),
        default_branch=details.default_branch.strip(),
        license=details.license.strip(),
        topics=tuple(t.strip() for t in details.topics if t.strip()),
        is_private=details.is_private,
        is_fork=details.is_fork,
        is_archived=details.is_archived,
        last_pushed_at=_git(folder, "log", "-1", "--format=%cI") or None,
        languages=with_percent(sizes),
        top_level=_top_level(folder),
        file_count=count,
        access_method="local_folder",
        tree_truncated=truncated,
        warnings=tuple(warnings),
        local_path=str(folder),
    )


def _top_level(folder: Path) -> tuple[Entry, ...]:
    try:
        children = [c for c in folder.iterdir() if c.name != ".git"]
    except OSError:
        return ()
    children.sort(key=lambda c: (not c.is_dir(), c.name.lower()))
    return tuple(Entry(c.name, "dir" if c.is_dir() else "file") for c in children[:MAX_TOP_LEVEL])


def _walk(folder: Path, sizes: dict[str, int]) -> tuple[int, bool]:
    """Count files and add up bytes per language. Returns the count and whether it stopped."""
    count = 0
    stack = [folder]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name not in _SKIP_DIRS:
                    stack.append(child)
                continue
            count += 1
            language = _LANGUAGES.get(child.suffix.lower())
            if language:
                with contextlib.suppress(OSError):
                    sizes[language] = sizes.get(language, 0) + child.stat().st_size
            if count >= MAX_FILES:
                return count, True
    return count, False
