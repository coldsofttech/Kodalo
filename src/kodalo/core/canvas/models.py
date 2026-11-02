"""Typed canvas data. A canvas is a named slide size that brand layouts refer to by id."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

CanvasName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
CanvasType = Literal["system", "user"]
MIN_SIZE = 200
MAX_SIZE = 4000
DEFAULT_CANVAS_ID = "system-instagram_portrait"


class Canvas(BaseModel):
    """A stored canvas. ``used_by`` lists the names of the layouts that use it."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: CanvasName
    width: int = Field(ge=MIN_SIZE, le=MAX_SIZE)
    height: int = Field(ge=MIN_SIZE, le=MAX_SIZE)
    type: CanvasType
    used_by: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
