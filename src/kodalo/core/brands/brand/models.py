"""Typed brand data: colors, fonts, logo and a reference to a shared layout (by id).

Every color has a light and a dark value. The ``*_alt`` colors and fonts are accents for emphasis
inside a slide. Values are validated so they can be used safely in generated CSS.
"""

from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from kodalo.core.brands.canvas.models import Canvas
from kodalo.core.brands.layout.models import DEFAULT_LAYOUT_ID, Layout

HexColor = Annotated[
    str,
    StringConstraints(min_length=7, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$"),
    AfterValidator(str.lower),
]

# Letters, digits, spaces and a few symbols: nothing that could end a CSS value.
FontFamily = Annotated[
    str, StringConstraints(min_length=1, max_length=100, pattern=r"^[\w .+&()-]+$")
]

LogoPosition = Literal[
    "top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right"
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ColorPair(_Strict):
    light: HexColor
    dark: HexColor


class BrandColors(_Strict):
    background: ColorPair
    primary: ColorPair
    secondary: ColorPair
    text: ColorPair
    background_alt: ColorPair
    primary_alt: ColorPair
    secondary_alt: ColorPair
    text_alt: ColorPair


class FontRef(_Strict):
    family: FontFamily
    source: Literal["bundled", "system"] = "bundled"


class BrandFonts(_Strict):
    heading: FontRef
    heading_alt: FontRef
    body: FontRef
    body_alt: FontRef
    mono: FontRef
    mono_alt: FontRef


class Logo(_Strict):
    """File names refer to files held by the logo store, never to paths."""

    file: Annotated[str, StringConstraints(max_length=64)] | None = None
    dark_file: Annotated[str, StringConstraints(max_length=64)] | None = None
    position: LogoPosition = "top_left"
    size_percent: int = Field(default=14, ge=5, le=60)
    padding: int = Field(default=48, ge=0, le=200)
    show_on: Literal["all", "first", "last", "none"] = "all"


class BrandData(_Strict):
    schema_version: Literal[1] = 1
    colors: BrandColors
    fonts: BrandFonts
    logo: Logo = Field(default_factory=Logo)
    layout_id: Annotated[str, StringConstraints(min_length=1, max_length=64)] = DEFAULT_LAYOUT_ID


ProfileName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class Brand(_Strict):
    """A stored brand profile."""

    id: str
    name: ProfileName
    is_default: bool
    data: BrandData
    layout: Layout = Field(description="The layout the layout_id refers to.")
    canvas: Canvas
    created_at: str
    updated_at: str
