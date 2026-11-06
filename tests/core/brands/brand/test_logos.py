from pathlib import Path

import pytest

from kodalo.core.brand import LogoError
from kodalo.core.brand.logos import MAX_LOGO_BYTES, LogoStore, detect_kind

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'


def test_png_and_svg_are_accepted() -> None:
    assert detect_kind(PNG) == "png"
    assert detect_kind(SVG) == "svg"


@pytest.mark.parametrize(
    "content",
    [
        b"GIF89a....",
        b"",
        b"\xff\xfe\x00",
        b"<html></html>",
        b"<svg><script>alert(1)</script></svg>",
        b'<svg onload="x()"></svg>',
        b'<svg xmlns:xlink="http://www.w3.org/1999/xlink"><image xlink:href="http://x/y.png"/></svg>',
        b'<svg><a href="javascript:alert(1)"><rect/></a></svg>',
        b"<svg><foreignObject><div/></foreignObject></svg>",
        b'<svg><style>@import url("http://x/y.css");</style></svg>',
        b'<svg><rect style="fill:url(http://x/y)"/></svg>',
        b'<!DOCTYPE svg [<!ENTITY a "aaaa">]><svg>&a;</svg>',
        b"<svg><use href='#a'/></svg>",
    ],
)
def test_unsafe_or_unknown_files_are_rejected(content: bytes) -> None:
    with pytest.raises(LogoError):
        detect_kind(content)


def test_oversized_file_is_rejected() -> None:
    with pytest.raises(LogoError):
        detect_kind(PNG + b"\x00" * MAX_LOGO_BYTES)


def test_local_references_in_svg_are_allowed() -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(#g)"/></svg>'
    assert detect_kind(svg) == "svg"


def test_store_round_trip_and_name_checks(tmp_path: Path) -> None:
    store = LogoStore(tmp_path)
    name = store.save(PNG)
    assert store.exists(name)
    assert store.read(name) == PNG
    store.delete(name)
    store.delete(None)
    assert not store.exists(name)
    with pytest.raises(LogoError):
        store.read(name)
    for bad in ("../x.png", "logo.png", "a" * 32 + ".exe"):
        assert not store.exists(bad)
        with pytest.raises(LogoError):
            store.path(bad)
