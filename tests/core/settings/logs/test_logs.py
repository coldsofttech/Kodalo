import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.settings.logs import (
    DEFAULT_LEVEL,
    DEFAULT_RETENTION_DAYS,
    LogConfig,
    LogSettings,
    LogsInvalidError,
    configure_file_logging,
    logs_dir,
    purge_expired_logs,
)
from kodalo.core.storage import Database, database_path


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[LogSettings]:
    database = Database.open(database_path(tmp_path))
    yield LogSettings(database)
    database.close()


@pytest.fixture(autouse=True)
def _clean_logger() -> Iterator[None]:
    yield
    logger = logging.getLogger("kodalo")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_defaults(settings: LogSettings) -> None:
    config = settings.get()
    assert config.level == DEFAULT_LEVEL == "INFO"
    assert config.retention_days == DEFAULT_RETENTION_DAYS == 90


def test_save_keeps_the_other_value(settings: LogSettings) -> None:
    settings.save(level="debug")
    config = settings.save(retention_days=30)
    assert (config.level, config.retention_days) == ("DEBUG", 30)


@pytest.mark.parametrize("kwargs", [{"level": "LOUD"}, {"retention_days": 0}])
def test_save_rejects_bad_values(settings: LogSettings, kwargs: dict[str, object]) -> None:
    with pytest.raises(LogsInvalidError):
        settings.save(**kwargs)  # type: ignore[arg-type]


def test_writes_to_the_logs_folder_at_the_level(tmp_path: Path) -> None:
    configure_file_logging(tmp_path, LogConfig(level="WARNING"))
    logger = logging.getLogger("kodalo.test")
    logger.info("hidden")
    logger.warning("shown")
    for handler in logging.getLogger("kodalo").handlers:
        handler.flush()
    text = "".join(f.read_text(encoding="utf-8") for f in logs_dir(tmp_path).glob("*.log"))
    assert "shown" in text
    assert "hidden" not in text


def test_purge_removes_only_old_log_files(tmp_path: Path) -> None:
    old = tmp_path / "kodalo-2020-01-01.log"
    new = tmp_path / "kodalo-2099-01-01.log"
    other = tmp_path / "notes.txt"
    for path in (old, new, other):
        path.write_text("x")
    stamp = time.time() - 100 * 86400
    os.utime(old, (stamp, stamp))
    os.utime(other, (stamp, stamp))
    assert purge_expired_logs(tmp_path, 90) == 1
    assert not old.exists()
    assert new.exists()
    assert other.exists()
