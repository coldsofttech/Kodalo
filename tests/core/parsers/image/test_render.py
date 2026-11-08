from pathlib import Path

import pytest
from PIL import Image

from kodalo.core.parsers.image import render
from kodalo.core.parsers.image.render import RenderError, SlideRenderer


def _png(path: Path, size: tuple[int, int]) -> None:
    Image.new("RGB", size, (10, 20, 30)).save(path, "PNG")


def _runner(size: tuple[int, int] | None, calls: list[list[str]]):  # type: ignore[no-untyped-def]
    def run(command: list[str]) -> int:
        calls.append(command)
        if size is not None:
            shot = next(a for a in command if a.startswith("--screenshot=")).split("=", 1)[1]
            _png(Path(shot), size)
        return 0

    return run


def test_a_page_becomes_a_jpeg_of_the_canvas_size(tmp_path: Path) -> None:
    page = tmp_path / "slide.html"
    page.write_text("<p>Hi</p>", encoding="utf-8")
    calls: list[list[str]] = []
    target = tmp_path / "out" / "slide.jpg"

    SlideRenderer(Path("edge.exe"), _runner((1080, 1350), calls)).render(page, (1080, 1350), target)

    with Image.open(target) as picture:
        assert (picture.format, picture.size) == ("JPEG", (1080, 1350))
    command = calls[0]
    assert "--headless=new" in command
    assert "--window-size=1080,1350" in command
    assert command[-1].startswith("file:///")


def test_a_taller_screenshot_is_cut_to_the_canvas(tmp_path: Path) -> None:
    page = tmp_path / "slide.html"
    page.write_text("<p>Hi</p>", encoding="utf-8")
    target = tmp_path / "slide.jpg"

    SlideRenderer(Path("edge.exe"), _runner((1080, 1400), [])).render(page, (1080, 1350), target)

    with Image.open(target) as picture:
        assert picture.size == (1080, 1350)


def test_no_picture_from_edge_is_an_error(tmp_path: Path) -> None:
    page = tmp_path / "slide.html"
    page.write_text("<p>Hi</p>", encoding="utf-8")

    with pytest.raises(RenderError, match="could not draw"):
        SlideRenderer(Path("edge.exe"), _runner(None, [])).render(
            page, (1080, 1350), tmp_path / "slide.jpg"
        )


def test_a_missing_edge_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render, "find_edge", lambda: None)
    page = tmp_path / "slide.html"
    page.write_text("<p>Hi</p>", encoding="utf-8")

    with pytest.raises(RenderError, match="Edge is needed"):
        SlideRenderer().render(page, (1080, 1350), tmp_path / "slide.jpg")


@pytest.mark.integration
def test_the_real_edge_draws_a_page(tmp_path: Path) -> None:
    if render.find_edge() is None:
        pytest.skip("Microsoft Edge is not installed.")
    page = tmp_path / "slide.html"
    page.write_text(
        '<body style="margin:0;background:#123456"><h1>Hello</h1></body>', encoding="utf-8"
    )
    target = tmp_path / "slide.jpg"

    SlideRenderer().render(page, (540, 675), target)

    with Image.open(target) as picture:
        assert picture.size == (540, 675)
        red, _, blue = picture.convert("RGB").getpixel((500, 600))  # type: ignore[misc]
        assert blue > red
