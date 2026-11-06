import pytest
from pydantic import ValidationError

from kodalo.core.brands.brand import (
    STARTER_PALETTES,
    BrandData,
    ColorPair,
    FontRef,
    Logo,
    starter_brand,
)
from kodalo.core.brands.layout import LayoutSettings


def test_starter_brand_is_valid_and_normalised() -> None:
    data = starter_brand()
    assert data.layout_id == "system-default"
    assert ColorPair(light="#ABCDEF", dark="#000000").light == "#abcdef"


@pytest.mark.parametrize("value", ["red", "#fff", "#12345g", "#1234567", "url(x)"])
def test_bad_colors_are_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        ColorPair(light=value, dark="#000000")


@pytest.mark.parametrize("family", ["", "Inter; color:red", 'A"B', "a{b}", "x" * 101, "a\nb"])
def test_unsafe_font_names_are_rejected(family: str) -> None:
    with pytest.raises(ValidationError):
        FontRef(family=family)


def test_unknown_keys_are_rejected() -> None:
    payload = starter_brand().model_dump()
    payload["surprise"] = 1
    with pytest.raises(ValidationError):
        BrandData.model_validate(payload)


def test_brand_refers_to_a_layout_by_id() -> None:
    data = starter_brand()
    data.layout_id = "user-1"
    assert data.layout_id == "user-1"
    with pytest.raises(ValidationError):
        data.layout_id = ""


def test_layout_and_logo_limits() -> None:
    with pytest.raises(ValidationError):
        LayoutSettings(margin_side=-1)
    with pytest.raises(ValidationError):
        LayoutSettings(footer_text="line\nbreak")
    with pytest.raises(ValidationError):
        LayoutSettings(slides_count=0)
    assert LayoutSettings().slides_count == 6
    with pytest.raises(ValidationError):
        Logo(size_percent=90)


def test_every_starter_palette_passes_contrast() -> None:
    from kodalo.core.brands.brand import check_colors

    for palette in STARTER_PALETTES:
        failing = [r for r in check_colors(palette.colors) if not r.passes]
        assert failing == [], palette.key
