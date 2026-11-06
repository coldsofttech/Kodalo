"""Palettes: named sets of brand colors that new brands start from."""

from kodalo.core.palette.errors import (
    PaletteError,
    PaletteInvalidError,
    PaletteNameTakenError,
    PaletteNotFoundError,
    PaletteReadOnlyError,
)
from kodalo.core.palette.models import Palette
from kodalo.core.palette.service import PaletteService

__all__ = [
    "Palette",
    "PaletteError",
    "PaletteInvalidError",
    "PaletteNameTakenError",
    "PaletteNotFoundError",
    "PaletteReadOnlyError",
    "PaletteService",
]
