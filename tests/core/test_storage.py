import json
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from kodalo.core.storage import Database, DatabaseTooNewError, MigrationError, database_path
from kodalo.core.storage import database as database_module
from kodalo.core.storage.database import backup_path
from kodalo.core.storage.models import (
    VERSION_TABLE,
    Base,
    Feature,
    Repository,
    Tool,
)

TABLES = {
    "settings",
    "brand_profiles",
    "brand_colors",
    "brand_fonts",
    "brand_logos",
    "canvases",
    "palettes",
    "layouts",
    "fonts",
    "ai_connections",
    "ai_models",
    "repositories",
    "repository_languages",
    "repository_topics",
    "repository_entries",
    "repository_notable_dirs",
    "repository_manifests",
    "directory_patterns",
    "monorepo_signals",
    "repository_dependencies",
    "ignored_directories",
    "tools",
    "features",
    "feature_evidence",
    VERSION_TABLE,
}


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return database_path(tmp_path / "data")


def test_fresh_database_migrates_to_latest(db_path: Path) -> None:
    db = Database.open(db_path)
    try:
        assert set(inspect(db.engine).get_table_names()) == TABLES
        with db.engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM schema_migrations")).scalar()
    finally:
        db.close()


def test_models_match_migrations(db_path: Path) -> None:
    db = Database.open(db_path)
    try:
        with db.engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"version_table": VERSION_TABLE})
            assert compare_metadata(context, Base.metadata) == []
    finally:
        db.close()


def test_reopening_keeps_data(db_path: Path) -> None:
    db = Database.open(db_path)
    with db.session() as session:
        session.add(Repository(url="https://github.com/a/b", owner="a", name="b"))
    db.close()

    reopened = Database.open(db_path)
    try:
        with reopened.session() as session:
            assert session.query(Repository).one().name == "b"
    finally:
        reopened.close()


def test_failed_migration_restores_existing_data(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = Database.open(db_path)
    with db.session() as session:
        session.add(Repository(url="https://github.com/a/b", owner="a", name="b"))
    db.close()
    # Pretend the stored version is older, so a migration runs and then fails half way.
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE schema_migrations SET version_num = '0000'")
    monkeypatch.setattr(database_module, "_is_known", lambda *_: True)

    def broken_upgrade(config: object, revision: str) -> None:
        with sqlite3.connect(db_path) as connection:
            connection.execute("DROP TABLE repositories")
        raise RuntimeError("boom")

    monkeypatch.setattr(command, "upgrade", broken_upgrade)
    with pytest.raises(MigrationError):
        Database.open(db_path)
    monkeypatch.undo()

    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT name FROM repositories").fetchone() == ("b",)
    assert backup_path(db_path).exists()


def test_failed_first_migration_leaves_no_file(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_upgrade(config: object, revision: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(command, "upgrade", broken_upgrade)
    with pytest.raises(MigrationError):
        Database.open(db_path)
    assert not db_path.exists()


def test_newer_database_is_refused_and_untouched(db_path: Path) -> None:
    Database.open(db_path).close()
    db = Database.open(db_path)
    with db.engine.begin() as connection:
        connection.execute(text("UPDATE schema_migrations SET version_num = '9999'"))
    db.close()
    before = db_path.read_bytes()

    with pytest.raises(DatabaseTooNewError):
        Database.open(db_path)
    assert db_path.read_bytes() == before


def test_foreign_keys_and_checks_are_enforced(db_path: Path) -> None:
    db = Database.open(db_path)
    try:
        with pytest.raises(IntegrityError), db.session() as session:
            session.add(Tool(name="orphan", repository_id="missing"))
        with db.session() as session:
            tool = Tool(name="t")
            session.add(tool)
            session.flush()
            tool_id = tool.id
        with pytest.raises(IntegrityError), db.session() as session:
            session.add(Feature(tool_id=tool_id, name="f", status="made_up"))
    finally:
        db.close()


def test_rows_get_uuid_ids_and_utc_timestamps(db_path: Path) -> None:
    db = Database.open(db_path)
    try:
        with db.session() as session:
            repo = Repository(url="https://github.com/a/b", owner="a", name="b")
            session.add(repo)
            session.flush()
            assert len(repo.id) == 36
            assert repo.created_at.endswith("+00:00")
    finally:
        db.close()


def test_cut_short_migration_can_be_finished(db_path: Path) -> None:
    """SQLite keeps schema changes made before a failure, so a rerun must skip them."""
    db = Database.open(db_path)
    db.close()
    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE schema_migrations SET version_num = '0002'")
        connection.execute("DROP TABLE repository_languages")
        connection.execute("ALTER TABLE repositories DROP COLUMN local_path")

    reopened = Database.open(db_path)
    try:
        assert "repository_languages" in inspect(reopened.engine).get_table_names()
        columns = {c["name"] for c in inspect(reopened.engine).get_columns("repositories")}
        assert {"homepage", "local_path"} <= columns
    finally:
        reopened.close()


COLOR_NAMES = (
    "background",
    "background_alt",
    "primary",
    "primary_alt",
    "secondary",
    "secondary_alt",
    "text",
    "text_alt",
)


def test_brand_data_json_is_copied_into_brand_tables(db_path: Path) -> None:
    """Upgrading from 0003 moves each profile's JSON into the brand tables."""
    Database.open(db_path).close()
    pair = {"light": "#111111", "dark": "#eeeeee"}
    data = {
        "colors": dict.fromkeys(COLOR_NAMES, pair),
        "fonts": {
            name: {"family": "Lato", "source": "system"}
            for name in ("body", "body_alt", "heading", "heading_alt", "mono", "mono_alt")
        },
        "layout": {"canvas": {"preset": "custom", "width": 900, "height": 700}, "align": "center"},
        "logo": {"file": "a.png", "size_percent": 20},
    }
    with sqlite3.connect(db_path) as connection:
        for table in (
            "brand_logos",
            "brand_layouts",
            "brand_fonts",
            "brand_colors",
            "palettes",
            "canvases",
        ):
            connection.execute(f"DROP TABLE IF EXISTS {table}")
        connection.execute(
            "ALTER TABLE brand_profiles ADD COLUMN data_json TEXT NOT NULL DEFAULT '{}'"
        )
        connection.execute(
            "INSERT INTO brand_profiles (id, created_at, updated_at, name, is_default, data_json) "
            "VALUES ('p1', 't', 't', 'Old', 1, ?)",
            (json.dumps(data),),
        )
        connection.execute("UPDATE schema_migrations SET version_num = '0003'")

    db = Database.open(db_path)
    try:
        with db.engine.connect() as connection:
            color = connection.execute(text("SELECT text_alt_dark FROM brand_colors")).scalar()
            font = connection.execute(
                text(
                    "SELECT f.family, f.source FROM brand_fonts b JOIN fonts f "
                    "ON f.id = b.mono_alt_id"
                )
            ).one()
            layout = connection.execute(
                text(
                    "SELECT l.name, l.align, l.slides_count, c.type, c.name FROM brand_profiles p "
                    "JOIN layouts l ON l.id = p.layout_id JOIN canvases c ON c.id = l.canvas_id"
                )
            ).one()
            fonts = connection.execute(text("SELECT count(*) FROM fonts")).scalar()
            logo = connection.execute(text("SELECT file, size_percent FROM brand_logos")).one()
            canvases = connection.execute(text("SELECT count(*) FROM canvases")).scalar()
        assert color == "#eeeeee"
        assert tuple(font) == ("Lato", "system")
        assert fonts == 11
        assert tuple(layout) == ("Old layout", "center", 6, "user", "Custom 900x700")
        assert tuple(logo) == ("a.png", 20)
        assert canvases == 6
    finally:
        db.close()
