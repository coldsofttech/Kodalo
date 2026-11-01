import pytest

from kodalo.core.brand import BrandInvalidError, list_paths, set_value, starter_brand


def test_sets_color_text_bool_and_number() -> None:
    data = starter_brand()
    data = set_value(data, "colors.primary.light", "#ABCDEF")
    data = set_value(data, "layout.slide_numbers", "off")
    data = set_value(data, "layout.margin_side", "120")
    data = set_value(data, "fonts.body.family", "Lora")
    data = set_value(data, "layout.footer_text", "@kodalo")
    assert data.colors.primary.light == "#abcdef"
    assert data.layout.slide_numbers is False
    assert data.layout.margin_side == 120
    assert data.fonts.body.family == "Lora"
    assert data.layout.footer_text == "@kodalo"


def test_original_is_not_changed() -> None:
    data = starter_brand()
    set_value(data, "layout.align", "center")
    assert data.layout.align == "left"


def test_canvas_preset_sets_size() -> None:
    data = set_value(starter_brand(), "layout.canvas.preset", "instagram_square")
    assert (data.layout.canvas.width, data.layout.canvas.height) == (1080, 1080)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("colors.primary.light", "red"),
        ("colors.primary", "#ffffff"),
        ("colors.nope.light", "#ffffff"),
        ("nope", "x"),
        ("logo.file", "x"),
        ("schema_version", "2"),
        ("layout.margin_side", "wide"),
        ("layout.margin_side", "9999"),
        ("layout.slide_numbers", "maybe"),
        ("layout.align", "right"),
        ("layout.canvas.preset", "custom_not_real"),
        ("fonts.body.family", "a;b"),
    ],
)
def test_bad_changes_are_rejected(path: str, value: str) -> None:
    with pytest.raises(BrandInvalidError):
        set_value(starter_brand(), path, value)


def test_list_paths_excludes_read_only_and_groups() -> None:
    paths = list_paths(starter_brand())
    assert "colors.primary.light" in paths
    assert "layout.canvas.width" in paths
    assert "logo.file" not in paths
    assert "colors.primary" not in paths
