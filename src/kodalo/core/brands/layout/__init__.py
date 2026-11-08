"""Layouts: named slide settings (canvas, margins, text, slide count) that brands share."""

from kodalo.core.brands.layout.errors import (
    LayoutError,
    LayoutInUseError,
    LayoutInvalidError,
    LayoutNameTakenError,
    LayoutNotFoundError,
    LayoutReadOnlyError,
)
from kodalo.core.brands.layout.models import DEFAULT_LAYOUT_ID, Layout, LayoutSettings
from kodalo.core.brands.layout.service import LayoutService

__all__ = [
    "DEFAULT_LAYOUT_ID",
    "Layout",
    "LayoutError",
    "LayoutInUseError",
    "LayoutInvalidError",
    "LayoutNameTakenError",
    "LayoutNotFoundError",
    "LayoutReadOnlyError",
    "LayoutService",
    "LayoutSettings",
]
