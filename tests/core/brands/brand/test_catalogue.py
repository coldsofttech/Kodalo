from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.brand import BrandService
from kodalo.core.brand import fonts as fonts_module
from kodalo.core.brand.fonts import FontInfo
from kodalo.core.storage import Database, database_path


@pytest.fixture
def brands(tmp_path: Path) -> Iterator[BrandService]:
    database = Database.open(database_path(tmp_path))
    yield BrandService(database, tmp_path)
    database.close()


def test_catalogue_is_seeded_with_the_bundled_fonts(brands: BrandService) -> None:
    listed = brands.fonts.list_fonts(system=False)
    assert [f.source for f in listed] == ["bundled"] * 10
    assert listed[0] == FontInfo("Inter", "sans", "bundled")


def test_installed_fonts_join_the_catalogue(
    brands: BrandService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        fonts_module, "system_fonts", lambda: [FontInfo("Segoe UI", "sans", "system")]
    )
    listed = brands.fonts.list_fonts()
    assert listed[-1] == FontInfo("Segoe UI", "sans", "system")
    assert len(listed) == 11
    # Without installed fonts the catalogue keeps the entry but the bundled list is shown.
    assert len(brands.fonts.list_fonts(system=False)) == 10


def test_a_brand_adds_an_unknown_font_to_the_catalogue(brands: BrandService) -> None:
    data = brands.starter()
    data.fonts.body.family = "Lato"
    data.fonts.body.source = "system"
    brand = brands.create("A", data)
    assert (brand.data.fonts.body.family, brand.data.fonts.body.source) == ("Lato", "system")
    again = brands.create("B", data)
    assert again.data.fonts.body.family == "Lato"
