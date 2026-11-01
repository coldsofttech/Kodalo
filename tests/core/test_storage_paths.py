from pathlib import Path

import pytest

from kodalo.core.storage import database_path, default_data_dir


def test_default_data_dir_uses_local_app_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_data_dir() == tmp_path / "Kodalo"


def test_default_data_dir_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert default_data_dir() == tmp_path / ".local" / "share" / "Kodalo"


def test_database_path(tmp_path: Path) -> None:
    assert database_path(tmp_path) == tmp_path / "kodalo.db"
