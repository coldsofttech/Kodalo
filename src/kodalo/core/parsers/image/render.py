"""Turn slide pages into JPEG pictures with Microsoft Edge, which comes with Windows.

Each page is opened by a headless Edge at the canvas size and photographed, so the picture is what
the preview shows, fonts and all. Edge only makes PNG, and Instagram only takes JPEG, so the
screenshot is converted with Pillow. Nothing is loaded from the internet: the pages carry all they
show.
"""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from PIL import Image, UnidentifiedImageError

JPEG_QUALITY = 92
_TIMEOUT = 60
_EDGE_FOLDERS = ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")

Runner = Callable[[list[str]], int]


class RenderError(Exception):
    """A slide could not be turned into a picture. The message is fit to show the user."""


def find_edge() -> Path | None:
    """Microsoft Edge on this computer, or ``None``."""
    found = shutil.which("msedge")
    if found:
        return Path(found)
    for variable in _EDGE_FOLDERS:
        base = os.environ.get(variable)
        if base:
            candidate = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    return None


def _run(command: list[str]) -> int:
    try:
        return subprocess.run(  # noqa: S603
            command, capture_output=True, timeout=_TIMEOUT, check=False
        ).returncode
    except (OSError, subprocess.TimeoutExpired):
        return -1


class SlideRenderer:
    """Photographs slide pages."""

    def __init__(self, edge: Path | None = None, runner: Runner | None = None) -> None:
        self._edge = edge
        self._run = runner if runner is not None else _run

    def render(self, page: Path, size: tuple[int, int], target: Path) -> None:
        """Write the picture of ``page`` at ``size`` (width, height) as a JPEG to ``target``.
        Raises ``RenderError`` when Edge is missing or does not make a picture."""
        edge = self._edge or find_edge()
        if edge is None:
            raise RenderError("Microsoft Edge is needed to make the pictures and was not found.")
        width, height = size
        with tempfile.TemporaryDirectory() as folder:
            shot = Path(folder) / "slide.png"
            command = [
                str(edge),
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={width},{height}",
                f"--user-data-dir={Path(folder) / 'profile'}",
                f"--screenshot={shot}",
                page.resolve().as_uri(),
            ]
            code = self._run(command)
            if not shot.is_file():
                raise RenderError(f"Edge could not draw the slide (exit code {code}).")
            _to_jpeg(shot, size, target)


def _to_jpeg(shot: Path, size: tuple[int, int], target: Path) -> None:
    """The screenshot as a JPEG exactly ``size`` big: Edge may leave a margin or add a strip."""
    try:
        with Image.open(shot) as image:
            picture = image.convert("RGB")
    except (OSError, UnidentifiedImageError) as error:
        raise RenderError("Edge made a picture that could not be read.") from error
    if picture.size != size:
        big_enough = picture.width >= size[0] and picture.height >= size[1]
        picture = picture.crop((0, 0, *size)) if big_enough else picture.resize(size)
    target.parent.mkdir(parents=True, exist_ok=True)
    picture.save(target, "JPEG", quality=JPEG_QUALITY, optimize=True)
