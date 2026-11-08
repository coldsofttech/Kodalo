"""Daily plain-text log files in ``<data folder>/logs``, shared by the command line, the API and
the window. Everything under the ``kodalo`` logger is written there."""

import logging
import time
from contextlib import suppress
from datetime import date
from pathlib import Path

from kodalo.core.settings.logs.service import LogConfig, LogSettings
from kodalo.core.storage import Database, StorageError, database_path

LOGGER_NAME = "kodalo"
LOGS_FOLDER = "logs"
FILE_PREFIX = "kodalo-"
FILE_SUFFIX = ".log"
FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def logs_dir(data_dir: Path) -> Path:
    """Return the folder that holds the log files."""
    return data_dir / LOGS_FOLDER


class DailyFileHandler(logging.FileHandler):
    """Write to ``kodalo-YYYY-MM-DD.log`` and move to a new file when the date changes."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._day = date.today()
        folder.mkdir(parents=True, exist_ok=True)
        super().__init__(self._path(self._day), encoding="utf-8", delay=True)

    def _path(self, day: date) -> Path:
        return self._folder / f"{FILE_PREFIX}{day.isoformat()}{FILE_SUFFIX}"

    def emit(self, record: logging.LogRecord) -> None:
        today = date.today()
        if today != self._day:
            self.acquire()
            try:
                self.close()
                self._day = today
                self.baseFilename = str(self._path(today))
            finally:
                self.release()
        super().emit(record)


def purge_expired_logs(folder: Path, retention_days: int) -> int:
    """Delete log files not written to for ``retention_days`` days; return how many went."""
    if not folder.is_dir():
        return 0
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for path in folder.glob(f"{FILE_PREFIX}*{FILE_SUFFIX}"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue  # a file in use or already gone is left for next time
    return removed


def configure_file_logging(data_dir: Path, config: LogConfig) -> None:
    """Apply ``config``: replace any earlier file handler, set the level and remove old files."""
    logger = logging.getLogger(LOGGER_NAME)
    for old in [h for h in logger.handlers if isinstance(h, DailyFileHandler)]:
        logger.removeHandler(old)
        old.close()
    folder = logs_dir(data_dir)
    try:
        handler = DailyFileHandler(folder)
    except OSError:
        return  # logging must never stop the program from starting
    handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(handler)
    logger.setLevel(config.level)
    purge_expired_logs(folder, config.retention_days)


def start_logging(data_dir: Path) -> None:
    """Start file logging with the saved settings, or the defaults (INFO, 90 days) when there is
    no database yet. Never fails and never creates a database."""
    config = LogConfig()
    path = database_path(data_dir)
    if path.is_file():
        try:
            database = Database.open(path)
        except (StorageError, OSError):
            database = None
        if database is not None:
            try:
                with suppress(Exception):  # unreadable settings fall back to the defaults
                    config = LogSettings(database).get()
            finally:
                database.close()
    configure_file_logging(data_dir, config)
