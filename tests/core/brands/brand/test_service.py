from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.brand import (
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
    BrandService,
    LogoError,
    starter_brand,
)
from kodalo.core.storage import Database, database_path

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'


@pytest.fixture
def service(tmp_path: Path) -> Iterator[BrandService]:
    database = Database.open(database_path(tmp_path))
    yield BrandService(database, tmp_path)
    database.close()


def test_first_profile_is_default_and_names_are_unique(service: BrandService) -> None:
    first = service.create("Main")
    second = service.create("Side")
    assert first.is_default
    assert not second.is_default
    assert service.default() == first
    with pytest.raises(BrandNameTakenError):
        service.create("main")
    assert [b.name for b in service.list_brands()] == ["Main", "Side"]


def test_empty_database_has_no_default(service: BrandService) -> None:
    assert service.default() is None
    assert service.list_brands() == []


@pytest.mark.parametrize("name", ["", "   ", "x" * 65])
def test_invalid_names(service: BrandService, name: str) -> None:
    with pytest.raises(BrandInvalidError):
        service.create(name)


def test_update_renames_and_replaces_data(service: BrandService) -> None:
    brand = service.create("Main")
    data = brand.data.model_copy(deep=True)
    data.logo.padding = 60
    updated = service.update(brand.id, name="Renamed", data=data)
    assert updated.name == "Renamed"
    assert service.get(brand.id).data.logo.padding == 60
    service.create("Other")
    with pytest.raises(BrandNameTakenError):
        service.update(brand.id, name="other")
    assert service.update(brand.id, name="Renamed").name == "Renamed"


def test_unknown_id(service: BrandService) -> None:
    for call in (
        lambda: service.get("nope"),
        lambda: service.update("nope", name="x"),
        lambda: service.set_default("nope"),
        lambda: service.delete("nope"),
        lambda: service.duplicate("nope", "x"),
    ):
        with pytest.raises(BrandNotFoundError):
            call()


def test_set_default_moves_the_flag(service: BrandService) -> None:
    first = service.create("A")
    second = service.create("B")
    assert service.set_default(second.id).is_default
    assert not service.get(first.id).is_default
    assert service.default() is not None
    assert service.default().id == second.id  # type: ignore[union-attr]


def test_deleting_default_promotes_another(service: BrandService) -> None:
    first = service.create("A")
    second = service.create("B")
    service.delete(first.id)
    assert service.get(second.id).is_default
    service.delete(second.id)
    assert service.default() is None


def test_logo_set_replace_remove(service: BrandService) -> None:
    brand = service.create("Main")
    with_logo = service.set_logo(brand.id, PNG)
    first_file = with_logo.data.logo.file
    assert first_file
    assert service.logos.exists(first_file)
    replaced = service.set_logo(brand.id, SVG)
    assert replaced.data.logo.file != first_file
    assert not service.logos.exists(first_file)
    dark = service.set_logo(brand.id, PNG, dark=True)
    assert dark.data.logo.dark_file
    cleared = service.remove_logo(brand.id, dark=True)
    assert cleared.data.logo.dark_file is None
    assert cleared.data.logo.file == replaced.data.logo.file


def test_bad_logo_is_rejected_and_nothing_is_kept(service: BrandService) -> None:
    brand = service.create("Main")
    with pytest.raises(LogoError):
        service.set_logo(brand.id, b"<svg><script/></svg>")
    assert service.get(brand.id).data.logo.file is None
    assert not list(service.logos.directory.glob("*")) if service.logos.directory.exists() else True


def test_data_may_only_reference_existing_logo_files(service: BrandService) -> None:
    data = starter_brand()
    data.logo.file = "a" * 32 + ".png"
    with pytest.raises(BrandInvalidError):
        service.create("Main", data)


def test_duplicate_copies_logo_files(service: BrandService) -> None:
    original = service.set_logo(service.create("Main").id, PNG)
    copy = service.duplicate(original.id, "Copy")
    assert not copy.is_default
    assert copy.data.logo.file
    assert copy.data.logo.file != original.data.logo.file
    assert service.logos.read(copy.data.logo.file) == PNG
    service.delete(original.id)
    assert service.logos.exists(copy.data.logo.file)


def test_duplicate_with_taken_name_leaves_no_stray_files(service: BrandService) -> None:
    original = service.set_logo(service.create("Main").id, PNG)
    with pytest.raises(BrandNameTakenError):
        service.duplicate(original.id, "Main")
    assert len(list(service.logos.directory.glob("*"))) == 1


def test_export_and_import_round_trip(service: BrandService) -> None:
    brand = service.set_logo(service.create("Main").id, PNG)
    payload = service.export_profile(brand.id)
    assert payload["format"] == "kodalo-brand"
    imported = service.import_profile(payload)
    assert imported.name == "Main (2)"
    assert imported.data.colors == brand.data.colors
    assert imported.data.logo.file
    assert imported.data.logo.file != brand.data.logo.file
    assert service.logos.read(imported.data.logo.file) == PNG
    renamed = service.import_profile(payload, name="Fresh")
    assert renamed.name == "Fresh"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(format="other"),
        lambda p: p.update(version=99),
        lambda p: p["data"]["colors"]["text"].update(light="red"),
        lambda p: p.update(logos={}),
        lambda p: p["logos"][next(iter(p["logos"]))].update(content_base64="!!notbase64"),
        lambda p: p["logos"][next(iter(p["logos"]))].update(
            content_base64="PHN2Zz48c2NyaXB0Lz48L3N2Zz4="
        ),
    ],
)
def test_bad_import_is_rejected_cleanly(service: BrandService, mutate: object) -> None:
    brand = service.set_logo(service.create("Main").id, PNG)
    payload = service.export_profile(brand.id)
    mutate(payload)  # type: ignore[operator]
    before = len(list(service.logos.directory.glob("*")))
    with pytest.raises((BrandInvalidError, LogoError)):
        service.import_profile(payload)
    assert len(service.list_brands()) == 1
    assert len(list(service.logos.directory.glob("*"))) == before


def test_contrast_through_service(service: BrandService) -> None:
    results = service.contrast(starter_brand())
    assert len(results) == 12
    assert all(r.passes for r in results)


def test_data_survives_reopening(tmp_path: Path) -> None:
    path = database_path(tmp_path)
    database = Database.open(path)
    created = BrandService(database, tmp_path).create("Main")
    database.close()
    reopened = Database.open(path)
    try:
        assert BrandService(reopened, tmp_path).get(created.id) == created
    finally:
        reopened.close()
