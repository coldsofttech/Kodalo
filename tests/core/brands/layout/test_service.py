from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.brands.brand import BrandService
from kodalo.core.brands.layout import (
    LayoutInUseError,
    LayoutInvalidError,
    LayoutNameTakenError,
    LayoutNotFoundError,
    LayoutReadOnlyError,
    LayoutSettings,
)
from kodalo.core.storage import Database, database_path


@pytest.fixture
def brands(tmp_path: Path) -> Iterator[BrandService]:
    database = Database.open(database_path(tmp_path))
    yield BrandService(database, tmp_path)
    database.close()


def test_three_built_in_layouts_with_six_slides(brands: BrandService) -> None:
    layouts = brands.layouts.list_layouts()
    assert [(lay.name, lay.type, lay.slides_count) for lay in layouts] == [
        ("Compact", "system", 6),
        ("Default", "system", 6),
        ("Spacious", "system", 6),
    ]
    assert brands.layouts.find("DEFAULT").id == "system-default"


def test_create_update_change_and_validation(brands: BrandService) -> None:
    layout = brands.layouts.create("Mine")
    assert (layout.type, layout.slides_count, layout.canvas_id) == (
        "user",
        6,
        "system-instagram_portrait",
    )
    renamed = brands.layouts.update(layout.id, name="Mine 2")
    assert renamed.name == "Mine 2"
    assert brands.layouts.change(layout.id, "slides_count", "9").slides_count == 9
    assert brands.layouts.change(layout.id, "slide_numbers", "off").slide_numbers is False
    assert brands.layouts.change(layout.id, "align", "center").align == "center"
    assert brands.layouts.change(layout.id, "canvas_id", "X landscape").canvas_id == (
        "system-x_landscape"
    )
    for path, value in (
        ("slides_count", "0"),
        ("slides_count", "many"),
        ("slide_numbers", "maybe"),
        ("align", "right"),
        ("nope", "1"),
        ("canvas_id", "missing"),
    ):
        with pytest.raises(LayoutInvalidError):
            brands.layouts.change(layout.id, path, value)
    with pytest.raises(LayoutNameTakenError):
        brands.layouts.create("default")
    with pytest.raises(LayoutInvalidError):
        brands.layouts.create("  ")
    with pytest.raises(LayoutNotFoundError):
        brands.layouts.get("nope")
    with pytest.raises(LayoutNotFoundError):
        brands.layouts.find("nope")


def test_built_in_layouts_are_read_only_but_can_be_copied(brands: BrandService) -> None:
    with pytest.raises(LayoutReadOnlyError):
        brands.layouts.update("system-default", name="Mine")
    with pytest.raises(LayoutReadOnlyError):
        brands.layouts.delete("system-default")
    copy = brands.layouts.duplicate("system-compact", "My compact")
    assert (copy.type, copy.density, copy.align) == ("user", "compact", "center")


def test_brands_share_a_layout_and_it_cannot_be_deleted_while_used(brands: BrandService) -> None:
    layout = brands.layouts.create("Shared", LayoutSettings(margin_top=10))
    data = brands.starter()
    data.layout_id = layout.id
    first, second = brands.create("A", data), brands.create("B", data)
    assert brands.layouts.get(layout.id).used_by == ["A", "B"]
    brands.layouts.change(layout.id, "margin_top", "20")
    assert brands.get(first.id).layout.margin_top == 20
    assert brands.get(second.id).layout.margin_top == 20
    with pytest.raises(LayoutInUseError) as error:
        brands.layouts.delete(layout.id)
    assert error.value.brands == ["A", "B"]
    brands.delete(first.id)
    brands.delete(second.id)
    brands.layouts.delete(layout.id)


def test_export_and_import(brands: BrandService) -> None:
    layout = brands.layouts.create("Mine", LayoutSettings(slides_count=8, footer_text="@k"))
    payload = brands.layouts.export_layout(layout.id)
    assert payload["format"] == "kodalo-layout"
    assert payload["canvas"] == {"name": "Instagram portrait", "width": 1080, "height": 1350}
    assert payload["slides_count"] == 8
    imported = brands.layouts.import_layout(payload)
    assert (imported.name, imported.slides_count, imported.footer_text) == ("Mine (2)", 8, "@k")
    assert brands.layouts.import_layout(payload, name="Other").name == "Other"
    for broken in (
        {**payload, "format": "x"},
        {**payload, "version": 2},
        {**payload, "slides_count": 0},
        {**payload, "canvas": {"name": "x"}},
    ):
        with pytest.raises(LayoutInvalidError):
            brands.layouts.import_layout(broken)
    with pytest.raises(LayoutInvalidError):
        brands.layouts.ensure("nope", "x")
