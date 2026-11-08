"""Typed canvas data. A canvas is a named slide size that brand layouts refer to by id."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

CanvasName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
CanvasType = Literal["system", "user"]
MIN_SIZE = 200
MAX_SIZE = 4000
DEFAULT_CANVAS_ID = "system-instagram_portrait"
CUSTOM_PLATFORM_ID = "custom"


class PlatformSize(BaseModel):
    """A size a social platform recommends."""

    model_config = ConfigDict(extra="forbid")

    name: str
    width: int
    height: int


class SocialPlatform(BaseModel):
    """A social network a canvas can be made for. ``custom`` recommends no sizes."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    sizes: list[PlatformSize] = Field(default_factory=list)


class Canvas(BaseModel):
    """A stored canvas. ``used_by`` lists the names of the layouts that use it."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: CanvasName
    width: int = Field(ge=MIN_SIZE, le=MAX_SIZE)
    height: int = Field(ge=MIN_SIZE, le=MAX_SIZE)
    type: CanvasType
    platform_id: str = CUSTOM_PLATFORM_ID
    platform: str = "Custom"
    size_concern: str | None = None
    used_by: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
