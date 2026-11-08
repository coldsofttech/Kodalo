"""Post a designed Studio post to Instagram.

The slide pages are stored in the data folder, photographed one by one by Edge into JPEGs, given a
temporary public address through cloudflared, and handed to Instagram together with the caption, the
hashtags and the alt text of the copy. A post with one slide is a single image; more is a carousel.
The pictures are deleted afterwards and the public address closes when the post is done.
"""

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from kodalo.core.brands.brand import Brand
from kodalo.core.parsers.image.render import SlideRenderer
from kodalo.core.settings.platforms import InstagramConnection, PublishedPost
from kodalo.core.studio.copy import Choice, CopyAssistant, PostCopy
from kodalo.core.studio.design import DesignAssistant, PageAssets
from kodalo.core.studio.errors import StudioInvalidError
from kodalo.core.tunnel import TunnelManager

MODES = ("light", "dark")


def caption_of(post: PostCopy) -> str:
    """The text posted with the pictures: the opening, the body, the call to action, the
    repository address and the hashtags, each as a paragraph."""
    caption = post.caption
    parts = [
        caption.opening,
        *caption.body,
        caption.cta,
        caption.repo_url,
        " ".join(post.hashtags),
    ]
    return "\n\n".join(part.strip() for part in parts if part.strip())


@dataclass(frozen=True)
class ExportedPost:
    """A post written to a folder: the pictures and the caption file."""

    folder: Path
    pictures: tuple[Path, ...]
    caption_file: Path


class InstagramPoster:
    """Turns a designed post into pictures and posts them."""

    def __init__(
        self,
        design: DesignAssistant,
        copy: CopyAssistant,
        instagram: InstagramConnection,
        data_dir: Path,
        *,
        tunnel: TunnelManager | None = None,
        renderer: SlideRenderer | None = None,
    ) -> None:
        self._design = design
        self._copy = copy
        self._instagram = instagram
        self._data_dir = data_dir
        self._tunnel = tunnel if tunnel is not None else TunnelManager(data_dir)
        self._renderer = renderer if renderer is not None else SlideRenderer()

    def tunnel_installed(self) -> bool:
        """Whether cloudflared, which posting needs, is already installed."""
        return self._tunnel.is_installed()

    def install_tunnel(self) -> None:
        """Install cloudflared when it is missing. Raises ``TunnelError`` when it cannot be
        installed."""
        self._tunnel.ensure_installed()

    def folder(self, choice: Choice) -> Path:
        """Where the pages of this post are kept in the data folder."""
        digest = hashlib.sha256(choice.key.encode("utf-8")).hexdigest()[:16]
        return self._data_dir / "designs" / choice.repo_id / digest

    def store_pages(self, choice: Choice, brand: Brand, assets: PageAssets) -> list[Path]:
        """Write the page of every slide, in light and dark, to the post's folder and return the
        ones for the light mode. Pages are rewritten, so they always match the saved design."""
        folder = self.folder(choice)
        folder.mkdir(parents=True, exist_ok=True)
        light: list[Path] = []
        number = 0
        while True:
            written = False
            for mode in MODES:
                page = self._design.slide_page(choice, number, brand, mode, assets)
                if page is None:
                    continue
                target = folder / f"slide-{number + 1}-{mode}.html"
                target.write_text(page, encoding="utf-8")
                written = True
                if mode == "light":
                    light.append(target)
            if not written:
                return light
            number += 1

    def post(
        self,
        choice: Choice,
        brand: Brand,
        assets: PageAssets,
        mode: str = "light",
    ) -> PublishedPost:
        """Post the designed post to Instagram. Raises ``StudioInvalidError`` when the canvas is
        not an Instagram one or the post has no saved copy and design; the Instagram, rendering and
        tunnel errors are raised as they are."""
        post = self._ready(choice, brand, assets, "Posting")
        pictures = self.folder(choice) / "pictures"
        shutil.rmtree(pictures, ignore_errors=True)
        try:
            files = self._render(choice, post, brand, mode, pictures)
            with self._tunnel.serve(files) as served:
                return self._instagram.publish(
                    served.urls, caption_of(post), [slide.alt_text for slide in post.slides]
                )
        finally:
            shutil.rmtree(pictures, ignore_errors=True)

    def export(
        self,
        choice: Choice,
        brand: Brand,
        assets: PageAssets,
        destination: str,
        mode: str = "light",
    ) -> ExportedPost:
        """Make the pictures of the designed post and write them, with ``caption.txt``, into a new
        folder inside ``destination``, so the post can be posted by hand. Raises
        ``StudioInvalidError`` when the canvas is not an Instagram one, the post has no saved copy
        and design, or ``destination`` is not a folder that can be written to; ``RenderError`` when
        the pictures cannot be made."""
        post = self._ready(choice, brand, assets, "Exporting")
        parent = _existing_folder(destination)
        target = _free_folder(parent, post.caption.opening)
        try:
            target.mkdir()
            files = self._render(choice, post, brand, mode, target)
            caption = target / "caption.txt"
            caption.write_text(_caption_file(post), encoding="utf-8")
        except OSError as error:
            shutil.rmtree(target, ignore_errors=True)
            raise StudioInvalidError("Kodalo could not write to that folder.") from error
        except BaseException:
            shutil.rmtree(target, ignore_errors=True)
            raise
        return ExportedPost(target, tuple(files), caption)

    def _ready(self, choice: Choice, brand: Brand, assets: PageAssets, doing: str) -> PostCopy:
        """The saved copy of a post that can be posted or exported, with its pages written."""
        if brand.canvas.platform_id != "instagram":
            raise StudioInvalidError(f"{doing} is only available for Instagram canvases.")
        post = self._copy.saved(choice)
        if post is None or self._design.saved(choice) is None:
            raise StudioInvalidError(f"Write and design the post before {doing.lower()} it.")
        self.store_pages(choice, brand, assets)
        return post

    def _render(
        self, choice: Choice, post: PostCopy, brand: Brand, mode: str, target: Path
    ) -> list[Path]:
        """Photograph every slide page into a JPEG in ``target``."""
        folder = self.folder(choice)
        files = []
        for number in range(1, len(post.slides) + 1):
            page = folder / f"slide-{number}-{'dark' if mode == 'dark' else 'light'}.html"
            picture = target / f"slide-{number}.jpg"
            self._renderer.render(page, (brand.canvas.width, brand.canvas.height), picture)
            files.append(picture)
        return files


def _caption_file(post: PostCopy) -> str:
    """The text of ``caption.txt``: the caption with its hashtags, then each slide's alt text."""
    text = caption_of(post)
    alts = [f"{n}. {slide.alt_text}" for n, slide in enumerate(post.slides, 1) if slide.alt_text]
    if alts:
        text += "\n\nAlt text for the pictures:\n" + "\n".join(alts)
    return text + "\n"


def _existing_folder(destination: str) -> Path:
    """``destination`` as a folder on this computer that exists."""
    if not destination or "\0" in destination or destination.startswith(("\\\\", "//")):
        raise StudioInvalidError("Choose a folder on this computer.")
    parent = Path(destination)
    if not parent.is_dir():
        raise StudioInvalidError("Choose a folder that exists.")
    return parent


def _free_folder(parent: Path, headline: str) -> Path:
    """A folder name inside ``parent`` made from the post's headline that is not taken yet."""
    slug = re.sub(r"[^a-z0-9]+", "-", headline.lower()).strip("-")[:40].strip("-") or "post"
    candidate = parent / slug
    number = 2
    while candidate.exists():
        candidate = parent / f"{slug}-{number}"
        number += 1
    return candidate
