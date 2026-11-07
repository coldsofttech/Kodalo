"""Logs: the level and retention of Kodalo's log files."""

from kodalo.core.settings.logs.errors import LogsInvalidError
from kodalo.core.settings.logs.files import (
    configure_file_logging,
    logs_dir,
    purge_expired_logs,
    start_logging,
)
from kodalo.core.settings.logs.service import (
    DEFAULT_LEVEL,
    DEFAULT_RETENTION_DAYS,
    LEVELS,
    MAX_RETENTION_DAYS,
    MIN_RETENTION_DAYS,
    LogConfig,
    LogLevel,
    LogSettings,
)

__all__ = [
    "DEFAULT_LEVEL",
    "DEFAULT_RETENTION_DAYS",
    "LEVELS",
    "MAX_RETENTION_DAYS",
    "MIN_RETENTION_DAYS",
    "LogConfig",
    "LogLevel",
    "LogSettings",
    "LogsInvalidError",
    "configure_file_logging",
    "logs_dir",
    "purge_expired_logs",
    "start_logging",
]
