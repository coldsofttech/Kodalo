"""Canvases: named slide sizes that brand layouts reuse."""

from kodalo.core.canvas.errors import (
    CanvasError,
    CanvasInUseError,
    CanvasInvalidError,
    CanvasNameTakenError,
    CanvasNotFoundError,
    CanvasReadOnlyError,
)
from kodalo.core.canvas.models import DEFAULT_CANVAS_ID, Canvas
from kodalo.core.canvas.service import CanvasService

__all__ = [
    "DEFAULT_CANVAS_ID",
    "Canvas",
    "CanvasError",
    "CanvasInUseError",
    "CanvasInvalidError",
    "CanvasNameTakenError",
    "CanvasNotFoundError",
    "CanvasReadOnlyError",
    "CanvasService",
]
