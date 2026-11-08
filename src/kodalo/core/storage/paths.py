"""Where the application keeps its data."""

import os
from pathlib import Path

APP_FOLDER = "Kodalo"
DATABASE_NAME = "kodalo.db"


def default_data_dir() -> Path:
    """Return the per-user data folder: ``%LOCALAPPDATA%/Kodalo`` on Windows."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_FOLDER


def database_path(data_dir: Path) -> Path:
    """Return the database file inside ``data_dir``."""
    return data_dir / DATABASE_NAME
