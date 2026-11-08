from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from kodalo.core.parsers.image.render import RenderError
from kodalo.core.settings.platforms import PublishedPost
from kodalo.core.studio.copy import Choice
from kodalo.core.studio.design import PageAssets
from kodalo.core.studio.errors import StudioInvalidError
from kodalo.core.studio.platforms.instagram.post import InstagramPoster, caption_of
from kodalo.core.tunnel import ServedImages

CHOICE = Choice("instagram", "r1", "feature", "features", "Hooks", "idea-1", "")


def _copy(slides: int = 3) -> Any:
    return SimpleNamespace(
        slides=[SimpleNamespace(alt_text=f"Alt {n}") for n in range(slides)],
        caption=SimpleNamespace(
            opening="Opening",
            body=("Line one", " "),
            cta="Read more.",
            repo_url="https://github.com/o/r",
        ),
        hashtags=("#a", "#b"),
    )


class FakeDesign:
    def __init__(self, slides: int = 3) -> None:
        self.slides = slides

    def saved(self, choice: Choice) -> object:
        return object()

    def slide_page(self, choice: Choice, index: int, brand: Any, mode: str, assets: Any) -> Any:
        return f"<p>{index}-{mode}</p>" if index < self.slides else None


class FakeCopy:
    def __init__(self, post: Any) -> None:
        self.post = post

    def saved(self, choice: Choice) -> Any:
        return self.post


class FakeInstagram:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    def publish(self, urls: Sequence[str], caption: str, alts: Sequence[str]) -> PublishedPost:
        self.sent.append((list(urls), caption, list(alts)))
        return PublishedPost("m1", "https://www.instagram.com/p/x/")


class FakeRenderer:
    def __init__(self) -> None:
        self.rendered: list[tuple[str, tuple[int, int]]] = []

    def render(self, page: Path, size: tuple[int, int], target: Path) -> None:
        self.rendered.append((page.name, size))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"jpeg")


class FakeTunnel:
    def __init__(self) -> None:
        self.served: list[list[str]] = []
        self.open = False
        self.installed = False

    def is_installed(self) -> bool:
        return self.installed

    def ensure_installed(self) -> Path:
        self.installed = True
        return Path("cloudflared.exe")

    @contextmanager
    def serve(self, files: Sequence[Path]) -> Iterator[ServedImages]:
        assert all(f.is_file() for f in files)
        self.served.append([f.name for f in files])
        self.open = True
        try:
            yield ServedImages(tuple(f"https://t.test/{f.name}?token=x" for f in files), ())
        finally:
            self.open = False


def _brand(platform: str = "instagram") -> Any:
    return SimpleNamespace(canvas=SimpleNamespace(platform_id=platform, width=1080, height=1350))


@pytest.fixture
def parts(tmp_path: Path) -> SimpleNamespace:
    instagram, renderer, tunnel = FakeInstagram(), FakeRenderer(), FakeTunnel()
    poster = InstagramPoster(
        FakeDesign(),  # type: ignore[arg-type]
        FakeCopy(_copy()),  # type: ignore[arg-type]
        instagram,  # type: ignore[arg-type]
        tmp_path,
        tunnel=tunnel,  # type: ignore[arg-type]
        renderer=renderer,  # type: ignore[arg-type]
    )
    return SimpleNamespace(
        poster=poster, instagram=instagram, renderer=renderer, tunnel=tunnel, data=tmp_path
    )


def test_the_caption_is_paragraphs_of_opening_body_call_to_action_repo_url_hashtags() -> None:
    assert caption_of(_copy()) == (
        "Opening\n\nLine one\n\nRead more.\n\nhttps://github.com/o/r\n\n#a #b"
    )


def test_pages_are_stored_in_the_data_folder_for_both_modes(parts: SimpleNamespace) -> None:
    light = parts.poster.store_pages(CHOICE, _brand(), PageAssets())

    folder = parts.poster.folder(CHOICE)
    assert folder.parent == parts.data / "designs" / "r1"
    assert [p.name for p in light] == [
        "slide-1-light.html",
        "slide-2-light.html",
        "slide-3-light.html",
    ]
    assert (folder / "slide-2-dark.html").read_text(encoding="utf-8") == "<p>1-dark</p>"


def test_every_slide_is_photographed_shared_and_posted_then_the_pictures_are_deleted(
    parts: SimpleNamespace,
) -> None:
    posted = parts.poster.post(CHOICE, _brand(), PageAssets(), "dark")

    assert posted.media_id == "m1"
    assert parts.renderer.rendered == [
        ("slide-1-dark.html", (1080, 1350)),
        ("slide-2-dark.html", (1080, 1350)),
        ("slide-3-dark.html", (1080, 1350)),
    ]
    assert parts.tunnel.served == [["slide-1.jpg", "slide-2.jpg", "slide-3.jpg"]]
    urls, caption, alts = parts.instagram.sent[0]
    assert urls[0] == "https://t.test/slide-1.jpg?token=x"
    assert caption.startswith("Opening")
    assert alts == ["Alt 0", "Alt 1", "Alt 2"]
    assert not parts.tunnel.open
    assert not (parts.poster.folder(CHOICE) / "pictures").exists()
    assert (parts.poster.folder(CHOICE) / "slide-1-dark.html").is_file()  # the pages stay


def test_cloudflared_is_checked_and_installed_on_request(parts: SimpleNamespace) -> None:
    before = parts.poster.tunnel_installed()

    parts.poster.install_tunnel()

    assert (before, parts.poster.tunnel_installed()) == (False, True)


def test_the_pictures_are_deleted_even_when_instagram_refuses(parts: SimpleNamespace) -> None:
    def refuse(*args: Any) -> PublishedPost:
        raise ValueError("refused")

    parts.instagram.publish = refuse

    with pytest.raises(ValueError, match="refused"):
        parts.poster.post(CHOICE, _brand(), PageAssets())

    assert not (parts.poster.folder(CHOICE) / "pictures").exists()
    assert not parts.tunnel.open


def test_only_an_instagram_canvas_can_be_posted(parts: SimpleNamespace) -> None:
    with pytest.raises(StudioInvalidError, match="Instagram canvases"):
        parts.poster.post(CHOICE, _brand("custom"), PageAssets())

    assert parts.renderer.rendered == []


def test_a_post_without_copy_or_design_cannot_be_posted(parts: SimpleNamespace) -> None:
    parts.poster._copy = FakeCopy(None)

    with pytest.raises(StudioInvalidError, match="Write and design"):
        parts.poster.post(CHOICE, _brand(), PageAssets())


def test_an_export_writes_the_pictures_and_the_caption_into_a_new_folder(
    parts: SimpleNamespace, tmp_path: Path
) -> None:
    destination = tmp_path / "chosen"
    destination.mkdir()

    exported = parts.poster.export(CHOICE, _brand(), PageAssets(), str(destination), "dark")

    assert exported.folder == destination / "opening"
    assert [p.name for p in exported.pictures] == ["slide-1.jpg", "slide-2.jpg", "slide-3.jpg"]
    assert all(p.is_file() for p in exported.pictures)
    assert [name for name, _ in parts.renderer.rendered] == [
        "slide-1-dark.html",
        "slide-2-dark.html",
        "slide-3-dark.html",
    ]
    caption = exported.caption_file.read_text(encoding="utf-8")
    assert caption.startswith("Opening\n\nLine one")
    assert "#a #b" in caption
    assert "Alt text for the pictures:\n1. Alt 0\n2. Alt 1\n3. Alt 2" in caption
    assert parts.instagram.sent == []  # nothing is sent anywhere
    assert parts.tunnel.served == []


def test_exporting_twice_never_overwrites_the_first_export(
    parts: SimpleNamespace, tmp_path: Path
) -> None:
    first = parts.poster.export(CHOICE, _brand(), PageAssets(), str(tmp_path))
    second = parts.poster.export(CHOICE, _brand(), PageAssets(), str(tmp_path))

    assert (first.folder.name, second.folder.name) == ("opening", "opening-2")
    assert first.caption_file.is_file()
    assert second.caption_file.is_file()


@pytest.mark.parametrize("destination", ["", "no-such-folder", "\\\\server\\share", "//server/x"])
def test_an_export_needs_a_folder_that_exists_on_this_computer(
    parts: SimpleNamespace, tmp_path: Path, destination: str
) -> None:
    with pytest.raises(StudioInvalidError, match="folder"):
        parts.poster.export(CHOICE, _brand(), PageAssets(), destination)

    assert parts.renderer.rendered == []


def test_a_failed_export_leaves_no_half_written_folder(
    parts: SimpleNamespace, tmp_path: Path
) -> None:
    def fail(page: Path, size: tuple[int, int], target: Path) -> None:
        raise RenderError("Microsoft Edge is needed.")

    parts.renderer.render = fail
    destination = tmp_path / "chosen"
    destination.mkdir()

    with pytest.raises(RenderError):
        parts.poster.export(CHOICE, _brand(), PageAssets(), str(destination))

    assert list(destination.iterdir()) == []


def test_only_an_instagram_canvas_can_be_exported(parts: SimpleNamespace, tmp_path: Path) -> None:
    with pytest.raises(StudioInvalidError, match="Instagram canvases"):
        parts.poster.export(CHOICE, _brand("custom"), PageAssets(), str(tmp_path))
