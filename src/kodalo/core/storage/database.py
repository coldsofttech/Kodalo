"""Open the local database, bringing it up to the latest version first."""

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.script.revision import RevisionError
from alembic.util import CommandError
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from kodalo.core.storage.errors import DatabaseTooNewError, MigrationError
from kodalo.core.storage.models import VERSION_TABLE

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def _make_engine(path: Path) -> Engine:
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection: Any, _record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def _current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"version_table": VERSION_TABLE})
        return context.get_current_revision()


def _is_known(script: ScriptDirectory, revision: str) -> bool:
    try:
        return script.get_revision(revision) is not None
    except (CommandError, RevisionError):
        return False


def head_revision() -> str | None:
    """Return the id of the newest migration this version of the application knows."""
    return ScriptDirectory.from_config(_config()).get_current_head()


def is_known_revision(revision: str) -> bool:
    """Return whether this version of the application knows the migration ``revision``."""
    return _is_known(ScriptDirectory.from_config(_config()), revision)


def backup_path(path: Path) -> Path:
    """Return the copy kept of the database from before the last migration."""
    return path.with_name(path.name + ".bak")


def migrate(path: Path) -> Engine:
    """Create or upgrade the database at ``path`` to the latest version and return its engine.

    Before a database that holds data is changed, a copy is kept next to it. If a migration fails,
    the copy is put back (or the new file removed), so existing data is never left half-migrated.
    A database written by a newer version of the application is refused and left alone.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    config = _config()
    script = ScriptDirectory.from_config(config)
    engine = _make_engine(path)
    try:
        current = _current_revision(engine)
        if current is not None and not _is_known(script, current):
            raise DatabaseTooNewError(
                "This data was created by a newer version of Kodalo. Update Kodalo to open it."
            )
    except Exception:
        engine.dispose()
        raise

    if current == script.get_current_head():
        return engine

    backup = backup_path(path)
    if existed and current is not None:
        shutil.copy2(path, backup)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    except Exception as exc:
        engine.dispose()
        if existed and current is not None:
            shutil.copy2(backup, path)
        else:
            path.unlink(missing_ok=True)
        raise MigrationError(
            "Updating the Kodalo data failed. Your existing data was left unchanged."
        ) from exc
    return engine


class Database:
    """The local SQLite database. Open it with :meth:`open`; close it when done."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False)

    @classmethod
    def open(cls, path: Path) -> "Database":
        """Open the database at ``path``, creating or migrating it as needed."""
        return cls(migrate(path))

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Yield a session that commits on success and rolls back on an error."""
        with self._sessions() as session:
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    def close(self) -> None:
        """Release the database file."""
        self.engine.dispose()
