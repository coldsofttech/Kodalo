"""Typed palette data: a name and the eight brand colors, each with a light and a dark value."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from kodalo.core.brand.models import BrandColors

PaletteName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
PaletteType = Literal["system", "user"]


class Palette(BaseModel):
    """A stored palette. ``system`` palettes are built in and read-only."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: PaletteName
    type: PaletteType
    colors: BrandColors
    created_at: str
    updated_at: str
