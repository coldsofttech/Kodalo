"""Typed layout data. A layout is a named set of slide settings that brands share."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from kodalo.core.brands.canvas.models import DEFAULT_CANVAS_ID

LayoutName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
LayoutType = Literal["system", "user"]
DEFAULT_LAYOUT_ID = "system-default"
DEFAULT_SLIDES = 6
MAX_SLIDES = 30


class LayoutSettings(BaseModel):
    """What a layout decides: the canvas, margins, corner radius, text and the number of slides."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    canvas_id: Annotated[str, StringConstraints(min_length=1, max_length=64)] = DEFAULT_CANVAS_ID
    margin_top: int = Field(default=96, ge=0, le=400)
    margin_side: int = Field(default=80, ge=0, le=400)
    margin_bottom: int = Field(default=96, ge=0, le=400)
    corner_radius: int = Field(default=24, ge=0, le=200)
    slide_numbers: bool = True
    footer_text: Annotated[str, StringConstraints(max_length=120, pattern=r"^[^\x00-\x1f]*$")] = ""
    align: Literal["left", "center"] = "left"
    density: Literal["compact", "regular", "spacious"] = "regular"
    slides_count: int = Field(default=DEFAULT_SLIDES, ge=1, le=MAX_SLIDES)


class Layout(LayoutSettings):
    """A stored layout. ``used_by`` lists the names of the brands that use it."""

    id: str
    name: LayoutName
    type: LayoutType
    used_by: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
