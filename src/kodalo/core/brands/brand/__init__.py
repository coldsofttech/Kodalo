"""Brand profiles: colors, fonts, logo and layout, with starter palettes and contrast checks."""

from kodalo.core.brands.brand.contrast import ContrastResult, check_colors, contrast_ratio
from kodalo.core.brands.brand.edit import list_paths, set_value
from kodalo.core.brands.brand.errors import (
    BrandError,
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
    LogoError,
)
from kodalo.core.brands.brand.fonts import FontInfo, available_fonts, bundled_fonts, missing_fonts
from kodalo.core.brands.brand.models import (
    Brand,
    BrandColors,
    BrandData,
    BrandFonts,
    ColorPair,
    FontRef,
    Logo,
)
from kodalo.core.brands.brand.palettes import STARTER_PALETTES, Palette, get_palette, starter_brand
from kodalo.core.brands.brand.service import BrandService

__all__ = [
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
    "ColorPair",
    "ContrastResult",
    "FontInfo",
    "FontRef",
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
