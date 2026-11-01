"""WCAG contrast checks for a brand's colors. They report; they never change a color."""

from dataclasses import dataclass
from typing import Literal

from kodalo.core.brand.models import BrandColors, ColorPair

TEXT_MINIMUM = 4.5
ACCENT_MINIMUM = 3.0

Mode = Literal["light", "dark"]


@dataclass(frozen=True)
class ContrastResult:
    """The contrast of one foreground color on one background color."""

    foreground: str
    background: str
    mode: Mode
    ratio: float
    minimum: float

    @property
    def passes(self) -> bool:
        return self.ratio >= self.minimum


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    """Return the relative luminance of ``#rrggbb``."""
    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio, from 1 to 21, rounded to two decimals."""
    a, b = luminance(foreground), luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _value(pair: ColorPair, mode: Mode) -> str:
    return pair.light if mode == "light" else pair.dark


def check_colors(colors: BrandColors) -> list[ContrastResult]:
    """Check text and accent colors on their backgrounds, in light and dark.

    Text must reach 4.5:1 and primary and secondary colors 3:1 (large text and graphics).
    """
    pairs: list[tuple[str, ColorPair, str, ColorPair, float]] = [
        ("text", colors.text, "background", colors.background, TEXT_MINIMUM),
        ("primary", colors.primary, "background", colors.background, ACCENT_MINIMUM),
        ("secondary", colors.secondary, "background", colors.background, ACCENT_MINIMUM),
        ("text_alt", colors.text_alt, "background_alt", colors.background_alt, TEXT_MINIMUM),
        (
            "primary_alt",
            colors.primary_alt,
            "background_alt",
            colors.background_alt,
            ACCENT_MINIMUM,
        ),
        (
            "secondary_alt",
            colors.secondary_alt,
            "background_alt",
            colors.background_alt,
            ACCENT_MINIMUM,
        ),
    ]
    results: list[ContrastResult] = []
    for fg_name, fg, bg_name, bg, minimum in pairs:
        for mode in ("light", "dark"):
            results.append(
                ContrastResult(
                    fg_name,
                    bg_name,
                    mode,
                    contrast_ratio(_value(fg, mode), _value(bg, mode)),
                    minimum,
                )
            )
    return results
