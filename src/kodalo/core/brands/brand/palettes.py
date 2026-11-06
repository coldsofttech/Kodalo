"""Starter palettes, so a new brand never begins as an empty form."""

from dataclasses import dataclass

from kodalo.core.brands.brand.models import (
    BrandColors,
    BrandData,
    BrandFonts,
    ColorPair,
    FontRef,
)


@dataclass(frozen=True)
class Palette:
    key: str
    title: str
    colors: BrandColors


def _pair(light: str, dark: str) -> ColorPair:
    return ColorPair(light=light, dark=dark)


STARTER_PALETTES: tuple[Palette, ...] = (
    Palette(
        "midnight",
        "Midnight",
        BrandColors(
            background=_pair("#ffffff", "#0b1020"),
            primary=_pair("#2563eb", "#60a5fa"),
            secondary=_pair("#7c3aed", "#a78bfa"),
            text=_pair("#111827", "#f3f4f6"),
            background_alt=_pair("#f1f5f9", "#151b30"),
            primary_alt=_pair("#1d4ed8", "#93c5fd"),
            secondary_alt=_pair("#6d28d9", "#c4b5fd"),
            text_alt=_pair("#0f172a", "#e5e7eb"),
        ),
    ),
    Palette(
        "paper",
        "Paper",
        BrandColors(
            background=_pair("#faf7f2", "#1c1917"),
            primary=_pair("#b45309", "#fbbf24"),
            secondary=_pair("#0f766e", "#5eead4"),
            text=_pair("#1c1917", "#f5f5f4"),
            background_alt=_pair("#f0e9dd", "#292524"),
            primary_alt=_pair("#92400e", "#fcd34d"),
            secondary_alt=_pair("#115e59", "#99f6e4"),
            text_alt=_pair("#292524", "#e7e5e4"),
        ),
    ),
    Palette(
        "graphite",
        "Graphite",
        BrandColors(
            background=_pair("#ffffff", "#0a0a0a"),
            primary=_pair("#111827", "#fafafa"),
            secondary=_pair("#6b7280", "#a3a3a3"),
            text=_pair("#111827", "#fafafa"),
            background_alt=_pair("#f3f4f6", "#171717"),
            primary_alt=_pair("#374151", "#e5e5e5"),
            secondary_alt=_pair("#4b5563", "#a3a3a3"),
            text_alt=_pair("#111827", "#fafafa"),
        ),
    ),
)

DEFAULT_PALETTE = STARTER_PALETTES[0].key


def default_fonts() -> BrandFonts:
    return BrandFonts(
        heading=FontRef(family="Poppins"),
        heading_alt=FontRef(family="Space Grotesk"),
        body=FontRef(family="Inter"),
        body_alt=FontRef(family="Source Sans 3"),
        mono=FontRef(family="JetBrains Mono"),
        mono_alt=FontRef(family="Fira Code"),
    )


def get_palette(key: str) -> Palette | None:
    """Return the starter palette with the given key, or ``None``."""
    return next((p for p in STARTER_PALETTES if p.key == key), None)


def starter_brand(palette_key: str = DEFAULT_PALETTE) -> BrandData:
    """Return complete brand data built from a starter palette.

    Raises ``KeyError`` for an unknown palette key.
    """
    palette = get_palette(palette_key)
    if palette is None:
        raise KeyError(palette_key)
    return BrandData(colors=palette.colors.model_copy(deep=True), fonts=default_fonts())
