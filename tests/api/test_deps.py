import threading
import time
from pathlib import Path

import pytest

from kodalo.api import deps
from kodalo.core.storage import Database


def test_simultaneous_first_requests_open_the_database_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The window sends several requests at once; each must not migrate the database itself."""
    deps.configure(tmp_path / "data")
    real_open = Database.open
    opened: list[int] = []

    def slow_open(path: Path) -> Database:
        opened.append(1)
        time.sleep(0.05)  # long enough for the other threads to arrive
        return real_open(path)

    monkeypatch.setattr(Database, "open", staticmethod(slow_open))
    start = threading.Barrier(8)
    failures: list[BaseException] = []

    def request() -> None:
        try:
            start.wait()
            deps.get_brand_service()
        except BaseException as error:
            failures.append(error)

    threads = [threading.Thread(target=request) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    assert len(opened) == 1
