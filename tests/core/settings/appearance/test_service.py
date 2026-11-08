from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import select

from kodalo.core.settings.appearance import Appearance, AppearanceInvalidError
from kodalo.core.settings.appearance.service import DEFAULT_THEME, GROUP, THEME_KEY, THEMES
from kodalo.core.storage import Database, database_path
from kodalo.core.storage.models import Setting


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    database = Database.open(database_path(tmp_path))
    yield database
    database.close()


@pytest.fixture
def appearance(database: Database) -> Appearance:
    return Appearance(database)


def test_follows_the_system_by_default(appearance: Appearance) -> None:
    assert appearance.get() == "system"
    assert DEFAULT_THEME == "system"
    assert THEMES == ("system", "light", "dark")


@pytest.mark.parametrize("theme", ["light", "dark", "system"])
def test_saves_each_theme(appearance: Appearance, theme: str) -> None:
    assert appearance.save(theme) == theme
    assert appearance.get() == theme


def test_saving_again_replaces_the_theme(appearance: Appearance, database: Database) -> None:
    appearance.save("dark")
    appearance.save("light")
    assert appearance.get() == "light"
    with database.session() as session:
        rows = session.scalars(
            select(Setting).where(Setting.group_name == GROUP, Setting.key == THEME_KEY)
        ).all()
        assert len(rows) == 1


def test_the_theme_survives_reopening_the_database(tmp_path: Path) -> None:
    first = Database.open(database_path(tmp_path))
    Appearance(first).save("dark")
    first.close()
    second = Database.open(database_path(tmp_path))
    try:
        assert Appearance(second).get() == "dark"
    finally:
        second.close()


def test_rejects_an_unknown_theme_and_keeps_the_saved_one(appearance: Appearance) -> None:
    appearance.save("dark")
    with pytest.raises(AppearanceInvalidError, match="Unknown theme: sepia"):
        appearance.save("sepia")
    assert appearance.get() == "dark"


def test_an_unusable_stored_value_falls_back_to_the_default(
    appearance: Appearance, database: Database
) -> None:
    appearance.save("dark")
    with database.session() as session:
        row = session.scalars(select(Setting).where(Setting.key == THEME_KEY)).one()
        row.value = "sepia"
    assert appearance.get() == DEFAULT_THEME
    with database.session() as session:
        row = session.scalars(select(Setting).where(Setting.key == THEME_KEY)).one()
        row.value = "dark"
        row.data_type = "integer"
    assert appearance.get() == DEFAULT_THEME
