from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.api import deps


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test in an ``integration`` folder (core, cli, api, ui) as an integration test."""
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def _fresh_state(tmp_path: Path) -> Iterator[None]:
    """Give every API test its own empty data folder."""
    deps.configure(tmp_path / "api-data")
    yield
    deps.configure(None)
