"""Brand profiles: colors, fonts, logo and layout, with starter palettes and contrast checks."""

from kodalo.core.brand.contrast import ContrastResult, check_colors, contrast_ratio
from kodalo.core.brand.edit import list_paths, set_value
from kodalo.core.brand.errors import (
    BrandError,
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
    LogoError,
)
from kodalo.core.brand.fonts import FontInfo, available_fonts, bundled_fonts, missing_fonts
from kodalo.core.brand.models import (
    CANVAS_SIZES,
    Brand,
    BrandColors,
    BrandData,
    BrandFonts,
    Canvas,
    ColorPair,
    FontRef,
    Layout,
    Logo,
)
from kodalo.core.brand.palettes import STARTER_PALETTES, Palette, get_palette, starter_brand
from kodalo.core.brand.service import BrandService

__all__ = [
    "CANVAS_SIZES",
    "STARTER_PALETTES",
    "Brand",
    "BrandColors",
    "BrandData",
    "BrandError",
    "BrandFonts",
    "BrandInvalidError",
    "BrandNameTakenError",
    "BrandNotFoundError",
    "BrandService",
    "Canvas",
    "ColorPair",
    "ContrastResult",
    "FontInfo",
    "FontRef",
    "Layout",
    "Logo",
    "LogoError",
    "Palette",
    "available_fonts",
    "bundled_fonts",
    "check_colors",
    "contrast_ratio",
    "get_palette",
    "list_paths",
    "missing_fonts",
    "set_value",
    "starter_brand",
]
