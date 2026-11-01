"""Fonts a brand can use: a bundled list plus the fonts installed on this computer."""

import re
import sys
from dataclasses import dataclass
from typing import Literal

from kodalo.core.brand.models import FontRef

Category = Literal["sans", "serif", "display", "mono"]


@dataclass(frozen=True)
class FontInfo:
    family: str
    category: Category
    source: Literal["bundled", "system"]


# Open-licence (SIL OFL) families that the app ships with, so output looks the same everywhere.
BUNDLED_FONTS: tuple[FontInfo, ...] = (
    FontInfo("Inter", "sans", "bundled"),
    FontInfo("Poppins", "sans", "bundled"),
    FontInfo("Montserrat", "sans", "bundled"),
    FontInfo("Source Sans 3", "sans", "bundled"),
    FontInfo("Space Grotesk", "display", "bundled"),
    FontInfo("Playfair Display", "serif", "bundled"),
    FontInfo("Lora", "serif", "bundled"),
    FontInfo("JetBrains Mono", "mono", "bundled"),
    FontInfo("Fira Code", "mono", "bundled"),
    FontInfo("IBM Plex Mono", "mono", "bundled"),
)

_REGISTRY_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
_STYLE_WORDS = re.compile(
    r"\s+(Bold|Italic|Oblique|Regular|Light|Semilight|Semibold|Black|Medium|Thin|Heavy|"
    r"Condensed|Extra|Demi|Ultra)\b.*$",
    re.IGNORECASE,
)
_VALID_FAMILY = re.compile(r"^[\w .+&()-]+$")


def bundled_fonts() -> list[FontInfo]:
    """Return the fonts shipped with the app."""
    return list(BUNDLED_FONTS)


def _family_names(registry_name: str) -> list[str]:
    base = re.sub(r"\s*\([^)]*\)\s*$", "", registry_name)
    names = []
    for part in base.split(" & "):
        family = _STYLE_WORDS.sub("", part).strip()
        if family and _VALID_FAMILY.match(family):
            names.append(family)
    return names


def system_fonts() -> list[FontInfo]:
    """Return the font families installed on Windows, or an empty list elsewhere."""
    if sys.platform != "win32":
        return []
    import winreg

    families: set[str] = set()
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, _REGISTRY_KEY) as key:
                count = winreg.QueryInfoKey(key)[1]
                for index in range(count):
                    families.update(_family_names(winreg.EnumValue(key, index)[0]))
        except OSError:
            continue
    return [FontInfo(name, "sans", "system") for name in sorted(families, key=str.lower)]


def available_fonts() -> list[FontInfo]:
    """Return bundled fonts first, then installed fonts that are not already bundled."""
    bundled = bundled_fonts()
    taken = {font.family.lower() for font in bundled}
    return bundled + [font for font in system_fonts() if font.family.lower() not in taken]


def missing_fonts(fonts: list[FontRef]) -> list[FontRef]:
    """Return the given fonts that are neither bundled nor installed."""
    known = {font.family.lower() for font in available_fonts()}
    return [font for font in fonts if font.family.lower() not in known]
