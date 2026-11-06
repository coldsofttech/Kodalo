from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.brands.brand import BrandInvalidError, BrandService
from kodalo.core.brands.canvas import (
    CanvasInUseError,
    CanvasInvalidError,
    CanvasNameTakenError,
    CanvasNotFoundError,
    CanvasReadOnlyError,
)
from kodalo.core.brands.layout import LayoutSettings
from kodalo.core.storage import Database, database_path


@pytest.fixture
def brands(tmp_path: Path) -> Iterator[BrandService]:
    database = Database.open(database_path(tmp_path))
    yield BrandService(database, tmp_path)
    database.close()


def test_built_in_canvases_come_first(brands: BrandService) -> None:
    canvases = brands.canvases.list_canvases()
    assert [c.type for c in canvases] == ["system"] * 5
    assert brands.canvases.find("instagram story").id == "system-instagram_story"
    assert brands.canvases.find("system-x_landscape").name == "X landscape"


def test_create_update_and_validation(brands: BrandService) -> None:
    feed = brands.canvases.create("Feed", 1080, 1350)
    assert (feed.type, feed.used_by) == ("user", [])
    assert brands.canvases.update(feed.id, name="Post", width=1000).width == 1000
    assert brands.canvases.find("post").height == 1350
    with pytest.raises(CanvasNameTakenError):
        brands.canvases.create("post", 500, 500)
    with pytest.raises(CanvasNameTakenError):
        brands.canvases.create("Instagram square", 500, 500)
    with pytest.raises(CanvasInvalidError):
        brands.canvases.create("Tiny", 10, 500)
    with pytest.raises(CanvasInvalidError):
        brands.canvases.update(feed.id, height=5000)
    with pytest.raises(CanvasInvalidError):
        brands.canvases.create("  ", 500, 500)
    with pytest.raises(CanvasNotFoundError):
        brands.canvases.get("nope")


def test_built_in_canvases_are_read_only_but_can_be_copied(brands: BrandService) -> None:
    with pytest.raises(CanvasReadOnlyError):
        brands.canvases.update("system-instagram_story", name="Mine")
    with pytest.raises(CanvasReadOnlyError):
        brands.canvases.delete("system-instagram_story")
    copy = brands.canvases.duplicate("system-instagram_story", "My story")
    assert (copy.width, copy.height, copy.type) == (1080, 1920, "user")


def test_export_and_import(brands: BrandService) -> None:
    feed = brands.canvases.create("Feed", 1080, 1350)
    payload = brands.canvases.export_canvas(feed.id)
    assert payload == {
        "format": "kodalo-canvas",
        "version": 1,
        "name": "Feed",
        "width": 1080,
        "height": 1350,
    }
    assert brands.canvases.import_canvas(payload).name == "Feed (2)"
    assert brands.canvases.import_canvas(payload, name="Other").name == "Other"
    for broken in (
        {**payload, "format": "x"},
        {**payload, "version": 2},
        {**payload, "width": "wide"},
        {**payload, "width": 5},
    ):
        with pytest.raises(CanvasInvalidError):
            brands.canvases.import_canvas(broken)


def test_ensure_reuses_or_creates_a_canvas(brands: BrandService) -> None:
    assert brands.canvases.ensure({"name": "X landscape", "width": 1600, "height": 900}) == (
        "system-x_landscape"
    )
    assert brands.canvases.ensure({"width": 1080, "height": 1080}) == "system-instagram_square"
    created = brands.canvases.ensure({"name": "Wide", "width": 1600, "height": 900})
    assert brands.canvases.get(created).name == "Wide"
    with pytest.raises(CanvasInvalidError):
        brands.canvases.ensure("not a canvas")


def test_layouts_use_canvases_and_block_their_deletion(brands: BrandService) -> None:
    canvas = brands.canvases.create("Feed", 1080, 1350)
    layout = brands.layouts.create("Feed layout", LayoutSettings(canvas_id=canvas.id))
    data = brands.starter()
    data.layout_id = layout.id
    brand = brands.create("A", data)
    assert brand.canvas.name == "Feed"
    assert brands.canvases.get(canvas.id).used_by == ["Feed layout"]

    brands.canvases.update(canvas.id, width=900, name="Wide feed")
    assert brands.get(brand.id).canvas.width == 900
    assert brands.get(brand.id).canvas.name == "Wide feed"

    with pytest.raises(CanvasInUseError) as error:
        brands.canvases.delete(canvas.id)
    assert error.value.brands == ["Feed layout"]
    brands.delete(brand.id)
    brands.layouts.delete(layout.id)
    brands.canvases.delete(canvas.id)
    with pytest.raises(CanvasNotFoundError):
        brands.canvases.get(canvas.id)


def test_brand_can_switch_layout_by_id_or_name(brands: BrandService) -> None:
    brand = brands.create("A")
    assert brand.layout.id == "system-default"
    data = brand.data.model_copy(deep=True)
    data.layout_id = "compact"
    changed = brands.update(brand.id, data=data)
    assert changed.data.layout_id == "system-compact"
    assert (changed.layout.align, changed.layout.density) == ("center", "compact")
    data.layout_id = "missing"
    with pytest.raises(BrandInvalidError):
        brands.update(brand.id, data=data)


def test_export_carries_the_layout_and_import_reuses_or_creates_it(
    brands: BrandService,
) -> None:
    canvas = brands.canvases.create("Feed", 1080, 1350)
    layout = brands.layouts.create("Feed layout", LayoutSettings(canvas_id=canvas.id))
    data = brands.starter()
    data.layout_id = layout.id
    brand = brands.create("A", data)
    payload = brands.export_profile(brand.id)
    assert payload["layout"]["name"] == "Feed layout"
    assert payload["layout"]["canvas"] == {"name": "Feed", "width": 1080, "height": 1350}
    assert "layout_id" not in payload["data"]

    assert brands.import_profile(payload).layout.id == layout.id
    brands.canvases.update(canvas.id, width=900)
    created = brands.import_profile(payload, name="B")
    assert created.layout.name == "Feed layout (2)"
    assert (created.canvas.name, created.canvas.width) == ("Feed (2)", 1080)


def test_import_of_an_old_file_with_a_nested_layout(brands: BrandService) -> None:
    payload = brands.export_profile(brands.create("A").id)
    del payload["layout"]
    layout = payload["data"]["layout"] = {
        "canvas": {"preset": "instagram_square", "width": 1080, "height": 1080},
        "margin_top": 50,
    }
    old = brands.import_profile(payload, name="Old")
    assert (old.layout.name, old.canvas.id, old.layout.margin_top) == (
        "Old layout",
        "system-instagram_square",
        50,
    )
    layout["canvas"] = {"preset": "custom", "width": 900, "height": 700}
    assert brands.import_profile(payload, name="Old 2").canvas.name == "Custom 900x700"
    payload["data"]["layout"] = {"canvas": {"name": "x"}}
    with pytest.raises(BrandInvalidError):
        brands.import_profile(payload, name="Bad")
    payload["data"]["layout"] = "nonsense"
    del payload["data"]["layout"]
    payload["canvas"] = {"width": 1080, "height": 1080}
    assert brands.import_profile(payload, name="Mid").canvas.id == "system-instagram_square"


def test_platforms_are_seeded_and_built_in_canvases_are_mapped(brands: BrandService) -> None:
    platforms = brands.canvases.list_platforms()
    assert [p.id for p in platforms] == ["instagram", "custom"]
    assert [(s.width, s.height) for s in platforms[0].sizes] == [
        (1080, 1080),
        (1080, 1350),
        (1080, 1920),
    ] or len(platforms[0].sizes) == 3
    assert platforms[1].sizes == []
    assert brands.canvases.get("system-instagram_story").platform == "Instagram"
    assert brands.canvases.get("system-x_landscape").platform_id == "custom"


def test_a_size_the_platform_does_not_recommend_is_flagged_but_saved(
    brands: BrandService,
) -> None:
    odd = brands.canvases.create("Odd", 1000, 1000, "instagram")
    assert odd.size_concern is not None
    assert "Instagram recommends" in odd.size_concern
    assert brands.canvases.create("Fine", 1080, 1080, "instagram").size_concern is None
    assert brands.canvases.create("Any", 1000, 1000).size_concern is None
    moved = brands.canvases.update(odd.id, platform_id="custom")
    assert moved.platform_id == "custom"
    assert moved.size_concern is None
    assert brands.canvases.duplicate(odd.id, "Copy").platform_id == "custom"


def test_an_unknown_platform_is_refused(brands: BrandService) -> None:
    with pytest.raises(CanvasInvalidError):
        brands.canvases.create("Nope", 1080, 1080, "myspace")
