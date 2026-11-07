"""The icon of a repository: which files may be it, and what kind of image a file is.

The candidates come from the files read when the repository was added, because the full list of
files is not kept afterwards. The README analysis with AI picks one of them (or none). The
picked file is copied into the data folder, so designs never need the repository again.
"""

import posixpath
import re
from collections.abc import Iterable

from kodalo.core.repositories.models import Entry

MAX_CANDIDATES = 20
MAX_ICON_BYTES = 2 * 1024 * 1024
_EXTENSIONS = (".svg", ".png", ".webp", ".jpg", ".jpeg")
_NAME = re.compile(r"(icon|logo|favicon|brand|mark)", re.IGNORECASE)
_SKIPPED_DIRS = {"node_modules", "vendor", "dist", "build", "target", ".git", "__pycache__"}
_PREFERRED = {".svg": 0, ".png": 1, ".webp": 2, ".jpg": 3, ".jpeg": 3}


def icon_candidates(paths: Iterable[Entry]) -> tuple[str, ...]:
    """Image files whose name says icon, logo, favicon, brand or mark, best first: near the top of
    the repository, then vector images, then the shorter names."""
    found: list[tuple[int, int, int, str]] = []
    for entry in paths:
        if entry.type != "file":
            continue
        parts = entry.path.split("/")
        extension = posixpath.splitext(entry.path)[1].lower()
        if extension not in _EXTENSIONS or any(part in _SKIPPED_DIRS for part in parts[:-1]):
            continue
        if not _NAME.search(posixpath.basename(entry.path)):
            continue
        found.append((len(parts), _PREFERRED[extension], len(entry.path), entry.path))
    return tuple(path for *_, path in sorted(found))[:MAX_CANDIDATES]


def icon_type(data: bytes) -> str | None:
    """``png``, ``jpg``, ``webp`` or ``svg`` from the first bytes, or None for anything else."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    head = data[:512].lstrip().lower()
    if head.startswith((b"<svg", b"<?xml")) and b"<svg" in data[:2048].lower():
        return "svg"
    return None
