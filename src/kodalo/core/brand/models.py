"""Typed brand data: colors, fonts, logo and layout.

Every color has a light and a dark value. The ``*_alt`` colors and fonts are accents for emphasis
inside a slide. Values are validated so they can be used safely in generated CSS.
"""

from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

HexColor = Annotated[
    str,
    StringConstraints(min_length=7, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$"),
    AfterValidator(str.lower),
]

# Letters, digits, spaces and a few symbols: nothing that could end a CSS value.
FontFamily = Annotated[
    str, StringConstraints(min_length=1, max_length=100, pattern=r"^[\w .+&()-]+$")
]

CanvasPreset = Literal[
    "instagram_portrait",
    "instagram_square",
    "instagram_story",
    "linkedin_landscape",
    "x_landscape",
    "custom",
]

# Preset name -> (width, height) in pixels.
CANVAS_SIZES: dict[str, tuple[int, int]] = {
    "instagram_portrait": (1080, 1350),
    "instagram_square": (1080, 1080),
    "instagram_story": (1080, 1920),
    "linkedin_landscape": (1200, 627),
    "x_landscape": (1600, 900),
}

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
    show_on: Literal["all", "first", "last"] = "all"


class Canvas(_Strict):
    preset: CanvasPreset = "instagram_portrait"
    width: int = Field(default=1080, ge=200, le=4000)
    height: int = Field(default=1350, ge=200, le=4000)

    @model_validator(mode="after")
    def _preset_matches_size(self) -> Self:
        expected = CANVAS_SIZES.get(self.preset)
        if expected is not None and (self.width, self.height) != expected:
            raise ValueError(f"{self.preset} is {expected[0]}x{expected[1]} pixels")
        return self


class Layout(_Strict):
    canvas: Canvas = Field(default_factory=Canvas)
    margin_top: int = Field(default=96, ge=0, le=400)
    margin_side: int = Field(default=80, ge=0, le=400)
    margin_bottom: int = Field(default=96, ge=0, le=400)
    corner_radius: int = Field(default=24, ge=0, le=200)
    slide_numbers: bool = True
    footer_text: Annotated[str, StringConstraints(max_length=120, pattern=r"^[^\x00-\x1f]*$")] = ""
    align: Literal["left", "center"] = "left"
    density: Literal["compact", "regular", "spacious"] = "regular"


class BrandData(_Strict):
    schema_version: Literal[1] = 1
    colors: BrandColors
    fonts: BrandFonts
    logo: Logo = Field(default_factory=Logo)
    layout: Layout = Field(default_factory=Layout)


ProfileName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class Brand(_Strict):
    """A stored brand profile."""

    id: str
    name: ProfileName
    is_default: bool
    data: BrandData
    created_at: str
    updated_at: str
