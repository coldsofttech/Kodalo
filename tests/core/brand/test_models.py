import pytest
from pydantic import ValidationError

from kodalo.core.brand import (
    STARTER_PALETTES,
    BrandData,
    Canvas,
    ColorPair,
    FontRef,
    Layout,
    Logo,
    starter_brand,
)


def test_starter_brand_is_valid_and_normalised() -> None:
    data = starter_brand()
    assert data.layout.canvas.width == 1080
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


def test_canvas_preset_must_match_its_size() -> None:
    assert Canvas(preset="instagram_square", width=1080, height=1080)
    with pytest.raises(ValidationError):
        Canvas(preset="instagram_square", width=1080, height=1350)
    assert Canvas(preset="custom", width=900, height=900).width == 900


def test_layout_and_logo_limits() -> None:
    with pytest.raises(ValidationError):
        Layout(margin_side=-1)
    with pytest.raises(ValidationError):
        Layout(footer_text="line\nbreak")
    with pytest.raises(ValidationError):
        Logo(size_percent=90)


def test_every_starter_palette_passes_contrast() -> None:
    from kodalo.core.brand import check_colors

    for palette in STARTER_PALETTES:
        failing = [r for r in check_colors(palette.colors) if not r.passes]
        assert failing == [], palette.key
