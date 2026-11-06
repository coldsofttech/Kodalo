"""Palettes: named sets of brand colors that new brands start from."""

from kodalo.core.brands.palette.errors import (
    PaletteError,
    PaletteInvalidError,
    PaletteNameTakenError,
    PaletteNotFoundError,
    PaletteReadOnlyError,
)
from kodalo.core.brands.palette.models import Palette
from kodalo.core.brands.palette.service import PaletteService

__all__ = [
    "Palette",
    "PaletteError",
    "PaletteInvalidError",
    "PaletteNameTakenError",
    "PaletteNotFoundError",
    "PaletteReadOnlyError",
    "PaletteService",
]
