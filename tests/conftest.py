from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import pytest

from kodalo.api import deps


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
    yield
    MemorySecrets.values.clear()


@pytest.fixture(autouse=True)
def _own_data_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep every test away from the real data folder, even when a command is run without
    ``--data-dir``."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "local-app-data"))


@pytest.fixture(autouse=True)
def _fresh_state(tmp_path: Path) -> Iterator[None]:
    """Give every API test its own empty data folder."""
    deps.configure(tmp_path / "api-data")
    yield
    deps.configure(None)
