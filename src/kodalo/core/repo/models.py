"""What is read from a repository, as plain values."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Language:
    """A language with its size in bytes and its share of all bytes, in percent."""

    name: str
    bytes: int
    percent: float


@dataclass(frozen=True)
class Entry:
    """A file or folder at the top of the repository."""

    path: str
    type: Literal["file", "dir"]


@dataclass(frozen=True)
class LocalDetails:
    """What git cannot tell about a local folder. The first four are required."""

    owner: str = ""
    repo: str = ""
    license: str = ""
    default_branch: str = ""
    description: str = ""
    homepage: str = ""
    topics: tuple[str, ...] = ()
    is_private: bool = False
    is_fork: bool = False
    is_archived: bool = False


@dataclass(frozen=True)
class RepoInfo:
    """Everything read about one repository. ``id`` is empty until it is stored."""

    url: str
    owner: str
    name: str
    description: str = ""
    homepage: str = ""
    default_branch: str | None = None
    license: str | None = None
    topics: tuple[str, ...] = ()
    is_private: bool = False
    is_fork: bool = False
    is_archived: bool = False
    last_pushed_at: str | None = None
    languages: tuple[Language, ...] = ()
    top_level: tuple[Entry, ...] = ()
    file_count: int = 0
    access_method: str = ""
    tree_truncated: bool = False
    warnings: tuple[str, ...] = ()
    local_path: str = ""
    id: str = ""
    last_scanned_at: str | None = None


def with_percent(sizes: dict[str, int]) -> tuple[Language, ...]:
    """Turn ``{language: bytes}`` into languages, largest first, with percentages."""
    total = sum(sizes.values())
    ordered = sorted(sizes.items(), key=lambda item: (-item[1], item[0]))
    return tuple(
        Language(name, size, round(size * 100 / total, 1) if total else 0.0)
        for name, size in ordered
        if size > 0
    )
