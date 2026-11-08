import pytest

from kodalo.core.brands.brand import BrandInvalidError, list_paths, set_value, starter_brand


def test_sets_color_text_bool_and_number() -> None:
    data = starter_brand()
    data = set_value(data, "colors.primary.light", "#ABCDEF")
    data = set_value(data, "logo.padding", "120")
    data = set_value(data, "fonts.body.family", "Lora")
    data = set_value(data, "logo.show_on", "first")
    assert data.colors.primary.light == "#abcdef"
    assert data.logo.padding == 120
    assert data.fonts.body.family == "Lora"
    assert data.logo.show_on == "first"


def test_original_is_not_changed() -> None:
    data = starter_brand()
    set_value(data, "logo.position", "top_right")
    assert data.logo.position == "top_left"


def test_layout_id_can_be_set() -> None:
    data = set_value(starter_brand(), "layout_id", "system-compact")
    assert data.layout_id == "system-compact"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("colors.primary.light", "red"),
        ("colors.primary", "#ffffff"),
        ("colors.nope.light", "#ffffff"),
        ("nope", "x"),
        ("logo.file", "x"),
        ("schema_version", "2"),
        ("logo.padding", "wide"),
        ("logo.padding", "9999"),
        ("logo.position", "middle"),
        ("layout_id", ""),
        ("fonts.body.family", "a;b"),
    ],
)
def test_bad_changes_are_rejected(path: str, value: str) -> None:
    with pytest.raises(BrandInvalidError):
        set_value(starter_brand(), path, value)


def test_list_paths_excludes_read_only_and_groups() -> None:
    paths = list_paths(starter_brand())
    assert "colors.primary.light" in paths
    assert "layout_id" in paths
    assert "logo.file" not in paths
    assert "colors.primary" not in paths
