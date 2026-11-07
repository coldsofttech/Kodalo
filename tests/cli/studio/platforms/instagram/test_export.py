import json
from pathlib import Path
from typing import Any

import pytest

from tests.cli.studio.conftest import Studio


def test_export_writes_the_post_into_a_folder_and_says_where(
    studio: Studio, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kodalo.core.studio.platforms.instagram.post import ExportedPost, InstagramPoster

    seen: list[Any] = []

    def export(
        self: Any, choice: Any, brand: Any, assets: Any, folder: str, mode: str
    ) -> ExportedPost:
        seen.append((folder, mode))
        target = Path(folder) / "post"
        return ExportedPost(target, (target / "slide-1.jpg",), target / "caption.txt")

    monkeypatch.setattr(InstagramPoster, "export", export)

    code, out = studio.post("design", "export", "--folder", str(tmp_path), "--mode", "dark")
    as_json = studio.post("design", "export", "--folder", str(tmp_path), "--json")

    assert code == 0
    assert "Exported 1 picture(s)" in out
    assert seen[0] == (str(tmp_path), "dark")
    assert json.loads(as_json[1])["caption_file"].endswith("caption.txt")


def test_a_failed_export_is_an_error(studio: Studio, tmp_path: Path) -> None:
    code, _ = studio.post("design", "export", "--folder", str(tmp_path / "missing"))

    assert code == 1
