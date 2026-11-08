"""The log level and retention, kept in the ``settings`` table."""

from dataclasses import dataclass
from typing import Literal, get_args

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from kodalo.core.settings.logs.errors import LogsInvalidError
from kodalo.core.storage import Database
from kodalo.core.storage.models import Setting

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LEVELS: tuple[str, ...] = get_args(LogLevel)
DEFAULT_LEVEL: LogLevel = "INFO"
DEFAULT_RETENTION_DAYS = 90
MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 3650

GROUP = "logs"
LEVEL_KEY = "level"
RETENTION_KEY = "retention_days"


@dataclass(frozen=True)
class LogConfig:
    """How much Kodalo logs and for how long it keeps the files."""

    level: LogLevel = DEFAULT_LEVEL
    retention_days: int = DEFAULT_RETENTION_DAYS


class LogSettings:
    """The log level and how many days of log files are kept."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self) -> LogConfig:
        """Return the saved settings, using INFO and 90 days for anything not saved."""
        with self._database.session() as session:
            level = self._row(session, LEVEL_KEY)
            days = self._row(session, RETENTION_KEY)
            saved_level: LogLevel = DEFAULT_LEVEL
            if level is not None and level.value in LEVELS:
                saved_level = level.value  # type: ignore[assignment]
            return LogConfig(
                level=saved_level,
                retention_days=self._days(days.value if days is not None else None),
            )

    def save(self, level: str | None = None, retention_days: int | None = None) -> LogConfig:
        """Change the level and/or retention; anything left out keeps its current value."""
        if level is not None:
            level = level.upper()
            if level not in LEVELS:
                raise LogsInvalidError(
                    f"Unknown log level: {level}. Use one of: {', '.join(LEVELS)}."
                )
        if retention_days is not None and not (
            MIN_RETENTION_DAYS <= retention_days <= MAX_RETENTION_DAYS
        ):
            raise LogsInvalidError(
                f"Retention must be between {MIN_RETENTION_DAYS} and {MAX_RETENTION_DAYS} days."
            )
        with self._database.session() as session:
            if level is not None:
                self._store(session, LEVEL_KEY, level, "string")
            if retention_days is not None:
                self._store(session, RETENTION_KEY, str(retention_days), "integer")
        return self.get()

    @staticmethod
    def _days(raw: str | None) -> int:
        try:
            days = int(raw) if raw is not None else DEFAULT_RETENTION_DAYS
        except ValueError:
            return DEFAULT_RETENTION_DAYS
        return days if MIN_RETENTION_DAYS <= days <= MAX_RETENTION_DAYS else DEFAULT_RETENTION_DAYS

    def _store(self, session: Session, key: str, value: str, data_type: str) -> None:
        row = self._row(session, key)
        if row is None:
            row = Setting(scope="global", owner_id="", group_name=GROUP, key=key, mode="own")
            session.add(row)
        row.value = value
        row.data_type = data_type

    @staticmethod
    def _row(session: Session, key: str) -> Setting | None:
        query: Select[Setting] = select(Setting).where(
            Setting.scope == "global",
            Setting.owner_id == "",
            Setting.group_name == GROUP,
            Setting.key == key,
        )
        return session.scalars(query).first()
