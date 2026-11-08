"""Local SQLite storage: models, migrations and the database handle."""

from kodalo.core.storage.database import Database, head_revision, is_known_revision, migrate
from kodalo.core.storage.errors import DatabaseTooNewError, MigrationError, StorageError
from kodalo.core.storage.paths import database_path, default_data_dir

__all__ = [
    "Database",
    "DatabaseTooNewError",
    "MigrationError",
    "StorageError",
    "database_path",
    "default_data_dir",
    "head_revision",
    "is_known_revision",
    "migrate",
]
