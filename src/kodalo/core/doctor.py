"""Environment diagnostics: what is installed, and the state of the local data.

Checking is read-only. It never creates the data folder or the database and never changes a file.
"""

import os
import platform
import sqlite3
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from kodalo.core import __version__
from kodalo.core.brands.brand.fonts import bundled_fonts, system_fonts
from kodalo.core.storage import database_path, default_data_dir, head_revision, is_known_revision
from kodalo.core.storage.models import VERSION_TABLE

MIN_PYTHON = (3, 11)


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = False  # a failed required check makes the diagnosis fail

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _nearest_existing(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if candidate.exists():
            return candidate
    return path


def _data_folder(data_dir: Path) -> Check:
    if data_dir.is_dir():
        writable = os.access(data_dir, os.W_OK)
        detail = str(data_dir) if writable else f"{data_dir} (not writable)"
        return Check("Data folder", writable, detail, required=True)
    parent = _nearest_existing(data_dir)
    if parent.is_dir() and os.access(parent, os.W_OK):
        return Check("Data folder", True, f"{data_dir} (created on first use)")
    return Check("Data folder", False, f"{data_dir} cannot be created", required=True)


def _database(path: Path) -> list[Check]:
    if not path.is_file():
        return [Check("Database", True, "not created yet (created on first use)")]
    try:
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as error:
        return [Check("Database", False, f"cannot be opened: {error}", required=True)]
    try:
        try:
            row = connection.execute(f"SELECT version_num FROM {VERSION_TABLE}").fetchone()  # noqa: S608
        except sqlite3.Error:
            return [Check("Database", False, "is not a Kodalo database", required=True)]
        revision = row[0] if row else None
        head = head_revision()
        if revision is not None and not is_known_revision(revision):
            return [
                Check(
                    "Database",
                    False,
                    f"version {revision} is newer than this Kodalo; update Kodalo",
                    required=True,
                )
            ]
        state = "up to date" if revision == head else f"version {revision}; updates on next use"
        checks = [Check("Database", True, f"{path} ({state})")]
        if revision == head:
            try:
                count = connection.execute("SELECT COUNT(*) FROM brand_profiles").fetchone()[0]
                default = connection.execute(
                    "SELECT name FROM brand_profiles WHERE is_default = 1"
                ).fetchone()
            except sqlite3.Error:
                return checks
            detail = f"{count} (default: {default[0]})" if default else str(count)
            checks.append(Check("Brand profiles", True, detail))
        return checks
    finally:
        connection.close()


def run_checks(data_dir: Path | None = None) -> list[Check]:
    """Run every check and return the results. ``data_dir`` defaults to the per-user folder."""
    data_dir = data_dir or default_data_dir()
    python = sys.version_info
    checks = [
        Check("Kodalo", True, __version__),
        Check(
            "Python",
            python >= MIN_PYTHON,
            f"{python.major}.{python.minor}.{python.micro} "
            f"(requires {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)",
            required=True,
        ),
        Check("Platform", True, platform.platform()),
        _data_folder(data_dir),
        *_database(database_path(data_dir)),
    ]
    installed = len(system_fonts())
    checks.append(
        Check(
            "Fonts",
            True,
            f"{len(bundled_fonts())} bundled, {installed} installed"
            if installed
            else f"{len(bundled_fonts())} bundled (installed fonts are listed on Windows only)",
        )
    )
    return checks


def passed(checks: list[Check]) -> bool:
    """Return whether every required check succeeded."""
    return all(check.ok for check in checks if check.required)
