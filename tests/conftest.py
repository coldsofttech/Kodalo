import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import Engine

from kodalo.api import deps
from kodalo.core.storage import database as storage_database
from kodalo.core.storage import database_path

_real_migrate = storage_database.migrate


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test in an ``integration`` folder (core, cli, api, ui) as an integration test."""
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


class MemorySecrets:
    """An in-memory stand-in for the system keychain, shared so separate commands see one store."""

    values: ClassVar[dict[str, str]] = {}

    def get(self, ref: str) -> str | None:
        return self.values.get(ref)

    def set(self, ref: str, value: str) -> None:
        self.values[ref] = value

    def delete(self, ref: str) -> None:
        self.values.pop(ref, None)


@pytest.fixture(autouse=True)
def _memory_keychain(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep every test away from the real system keychain."""
    MemorySecrets.values.clear()
    monkeypatch.setattr("kodalo.core.ai.service.KeychainSecrets", MemorySecrets)
    monkeypatch.setattr("kodalo.core.settings.platforms.instagram.KeychainSecrets", MemorySecrets)
    yield
    MemorySecrets.values.clear()


@pytest.fixture(autouse=True)
def _own_data_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep every test away from the real data folder, even when a command is run without
    ``--data-dir``."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "local-app-data"))


@pytest.fixture(scope="session")
def _migrated_database(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A database at the latest version, built once per worker and copied into every test.

    Creating the tables takes a moment on a slow disk (a CI runner), and doing it in every test made
    the first request of each one wait long enough to time out."""
    folder = tmp_path_factory.mktemp("migrated-data")
    _real_migrate(database_path(folder)).dispose()
    return database_path(folder)


@pytest.fixture(autouse=True)
def _start_from_migrated_database(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, _migrated_database: Path
) -> None:
    """Let a new database start as a copy of the migrated one, so opening it skips the migration.

    The storage tests keep the real migration, since migrating is what they test."""
    if "storage" in request.path.parts:
        return

    def copy_then_migrate(path: Path) -> Engine:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_migrated_database, path)
        return _real_migrate(path)

    monkeypatch.setattr(storage_database, "migrate", copy_then_migrate)


@pytest.fixture(autouse=True)
def _fresh_state(tmp_path: Path) -> Iterator[None]:
    """Give every API test its own empty data folder."""
    deps.configure(tmp_path / "api-data")
    yield
    deps.configure(None)
