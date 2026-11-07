"""Logs routes: the log level and how long log files are kept."""

from fastapi import APIRouter, HTTPException, status

from kodalo.api.deps import data_dir
from kodalo.api.routers.common import COMMON, INVALID, LogSetting
from kodalo.api.schemas import LogsResponse, LogsUpdate
from kodalo.core.settings.logs import (
    LogConfig,
    LogsInvalidError,
    configure_file_logging,
    logs_dir,
)

router = APIRouter()


def _response(config: LogConfig) -> LogsResponse:
    return LogsResponse(
        level=config.level,
        retention_days=config.retention_days,
        folder=str(logs_dir(data_dir())),
    )


@router.get("/settings/logs", summary="Get the log settings", responses=COMMON)
def get_logs(settings: LogSetting) -> LogsResponse:
    """Return the log level, how many days log files are kept and where they are written."""
    return _response(settings.get())


@router.put("/settings/logs", summary="Change the log settings", responses=COMMON | INVALID)
def set_logs(body: LogsUpdate, settings: LogSetting) -> LogsResponse:
    """Change the log level and/or retention. The change applies straight away."""
    try:
        config = settings.save(body.level, body.retention_days)
    except LogsInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    configure_file_logging(data_dir(), config)
    return _response(config)
