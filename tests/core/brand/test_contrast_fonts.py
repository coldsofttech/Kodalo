import sys

import pytest

from kodalo.core.brand import FontRef, available_fonts, bundled_fonts, contrast_ratio, missing_fonts
from kodalo.core.brand import fonts as fonts_module


def test_contrast_ratio_known_values() -> None:
    assert contrast_ratio("#000000", "#ffffff") == 21.0
    assert contrast_ratio("#ffffff", "#ffffff") == 1.0
    assert contrast_ratio("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


def test_failing_pair_is_reported() -> None:
    from kodalo.core.brand import ColorPair, check_colors, starter_brand

    colors = starter_brand().colors
    colors.text = ColorPair(light="#eeeeee", dark="#f3f4f6")
    failing = [r for r in check_colors(colors) if not r.passes]
    assert {(r.foreground, r.mode) for r in failing} == {("text", "light")}


def test_bundled_fonts_are_listed_first_without_duplicates() -> None:
    names = [font.family for font in available_fonts()]
    assert names[: len(bundled_fonts())] == [font.family for font in bundled_fonts()]
    assert len(names) == len({name.lower() for name in names})


def test_missing_fonts() -> None:
    known = FontRef(family="Inter")
    unknown = FontRef(family="Not A Real Font Family", source="system")
    assert missing_fonts([known, unknown]) == [unknown]


@pytest.mark.parametrize(
    ("registry_name", "families"),
    [
        ("Arial (TrueType)", ["Arial"]),
        ("Segoe UI Bold Italic (TrueType)", ["Segoe UI"]),
        ("Cambria & Cambria Math (TrueType)", ["Cambria", "Cambria Math"]),
        ("Weird;Name (TrueType)", []),
    ],
)
def test_registry_names_become_families(registry_name: str, families: list[str]) -> None:
    assert fonts_module._family_names(registry_name) == families


def test_system_fonts_are_empty_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert fonts_module.system_fonts() == []


@pytest.mark.skipif(sys.platform != "win32", reason="reads the Windows registry")
def test_system_fonts_on_windows() -> None:
    assert all(font.source == "system" for font in fonts_module.system_fonts())
