import json
import shutil
import subprocess
import urllib.request
from typing import Any

import pytest

from kodalo.core.repositories.social_preview import gh_social_preview, image_type

PNG = b"\x89PNG\r\n\x1a\n" + b"data"


class _Response:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self._data[:size]


def _answer(monkeypatch: pytest.MonkeyPatch, node: dict[str, Any], code: int = 0) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "gh")
    stdout = json.dumps({"data": {"repository": node}})
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, code, stdout, ""),
    )


def test_image_type() -> None:
    assert image_type(PNG) == "png"
    assert image_type(b"\xff\xd8\xffdata") == "jpg"
    assert image_type(b"<html>") is None


def test_downloads_a_custom_image(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://repository-images.githubusercontent.com/1/x"
    _answer(monkeypatch, {"openGraphImageUrl": url, "usesCustomOpenGraphImage": True})
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Response(PNG))
    assert gh_social_preview("o", "r") == PNG


def test_no_image_when_not_custom_foreign_host_or_not_an_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://repository-images.githubusercontent.com/1/x"
    _answer(monkeypatch, {"openGraphImageUrl": url, "usesCustomOpenGraphImage": False})
    assert gh_social_preview("o", "r") is None
    _answer(
        monkeypatch,
        {"openGraphImageUrl": "https://evil.example/x", "usesCustomOpenGraphImage": True},
    )
    assert gh_social_preview("o", "r") is None
    _answer(monkeypatch, {"openGraphImageUrl": url, "usesCustomOpenGraphImage": True})
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _Response(b"<html>"))
    assert gh_social_preview("o", "r") is None
    _answer(monkeypatch, {}, code=1)
    assert gh_social_preview("o", "r") is None


def test_no_gh_means_no_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert gh_social_preview("o", "r") is None
