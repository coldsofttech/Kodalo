from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.brands.brand import STARTER_PALETTES, BrandInvalidError, BrandService
from kodalo.core.brands.palette import (
    PaletteInvalidError,
    PaletteNameTakenError,
    PaletteNotFoundError,
    PaletteReadOnlyError,
    PaletteService,
)
from kodalo.core.storage import Database, database_path


@pytest.fixture
def brands(tmp_path: Path) -> Iterator[BrandService]:
    database = Database.open(database_path(tmp_path))
    yield BrandService(database, tmp_path)
    database.close()


@pytest.fixture
def palettes(brands: BrandService) -> PaletteService:
    return brands.palettes


def test_built_in_palettes_match_the_starter_colors(palettes: PaletteService) -> None:
    listed = palettes.list_palettes()
    assert [(p.name, p.type) for p in listed] == [
        ("Graphite", "system"),
        ("Midnight", "system"),
        ("Paper", "system"),
    ]
    for starter in STARTER_PALETTES:
        assert palettes.find(starter.key).colors == starter.colors


def test_find_by_name_id_or_old_key(palettes: PaletteService) -> None:
    assert palettes.find("PAPER").id == "system-paper"
    assert palettes.find("system-paper").name == "Paper"
    assert palettes.find("paper").id == "system-paper"
    with pytest.raises(PaletteNotFoundError):
        palettes.find("neon")
    with pytest.raises(PaletteNotFoundError):
        palettes.get("neon")


def test_create_update_set_color_and_validation(palettes: PaletteService) -> None:
    colors = palettes.find("midnight").colors
    ocean = palettes.create("Ocean", colors)
    assert ocean.type == "user"
    assert palettes.update(ocean.id, name="Sea").name == "Sea"
    changed = palettes.set_color(ocean.id, "primary.light", "#ABCDEF")
    assert changed.colors.primary.light == "#abcdef"
    assert palettes.update(ocean.id, colors=colors).colors == colors
    for path, value in (("primary", "#ffffff"), ("nope.light", "#ffffff"), ("text.dark", "red")):
        with pytest.raises(PaletteInvalidError):
            palettes.set_color(ocean.id, path, value)
    with pytest.raises(PaletteNameTakenError):
        palettes.create("midnight", colors)
    with pytest.raises(PaletteInvalidError):
        palettes.create("  ", colors)


def test_built_in_palettes_are_read_only_but_can_be_copied(palettes: PaletteService) -> None:
    with pytest.raises(PaletteReadOnlyError):
        palettes.update("system-paper", name="Mine")
    with pytest.raises(PaletteReadOnlyError):
        palettes.delete("system-paper")
    copy = palettes.duplicate("system-paper", "My paper")
    assert copy.colors == palettes.get("system-paper").colors
    palettes.delete(copy.id)
    with pytest.raises(PaletteNotFoundError):
        palettes.get(copy.id)


def test_export_and_import(palettes: PaletteService) -> None:
    payload = palettes.export_palette("system-paper")
    assert (payload["format"], payload["name"]) == ("kodalo-palette", "Paper")
    assert palettes.import_palette(payload).name == "Paper (2)"
    assert palettes.import_palette(payload, name="Other").name == "Other"
    for broken in (
        {**payload, "format": "x"},
        {**payload, "version": 2},
        {**payload, "colors": {}},
    ):
        with pytest.raises(PaletteInvalidError):
            palettes.import_palette(broken)


def test_brands_start_from_a_palette_by_name(brands: BrandService) -> None:
    ocean = brands.palettes.duplicate("system-paper", "Ocean")
    assert brands.starter("ocean").colors == ocean.colors
    assert brands.starter().colors == brands.palettes.find("midnight").colors
    with pytest.raises(BrandInvalidError):
        brands.starter("neon")
