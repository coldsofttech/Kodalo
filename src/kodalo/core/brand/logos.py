"""Storage and checking of logo files.

Logos are stored under random names inside the data folder, so a user-supplied name or path never
reaches the file system. SVG files are rejected when they could run code or load anything from
outside the file.
"""

import re
import uuid
from pathlib import Path
from xml.etree import ElementTree

from kodalo.core.brand.errors import LogoError

MAX_LOGO_BYTES = 2 * 1024 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_NAME = re.compile(r"^[0-9a-f]{32}\.(png|svg)$")
_FORBIDDEN_TAGS = {
    "script",
    "foreignobject",
    "iframe",
    "object",
    "embed",
    "audio",
    "video",
    "animate",
    "set",
    "use",
}
_DOCTYPE = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
_UNSAFE_CSS = re.compile(r"@import|javascript:|expression\(|url\(\s*['\"]?\s*(?!#)", re.IGNORECASE)


def detect_kind(content: bytes) -> str:
    """Return ``png`` or ``svg`` for a valid logo, or raise :class:`LogoError`."""
    if len(content) > MAX_LOGO_BYTES:
        raise LogoError("The logo is larger than 2 MB.")
    if content.startswith(_PNG_SIGNATURE):
        return "png"
    _check_svg(content)
    return "svg"


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def _check_svg(content: bytes) -> None:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise LogoError("The logo must be a PNG or an SVG file.") from None
    if _DOCTYPE.search(text):
        raise LogoError("The SVG logo contains a DOCTYPE or entity, which is not allowed.")
    try:
        # DOCTYPE and entities were rejected above, so entity expansion attacks cannot occur.
        root = ElementTree.fromstring(text)  # noqa: S314
    except ElementTree.ParseError:
        raise LogoError("The logo must be a PNG or an SVG file.") from None
    if _local(root.tag) != "svg":
        raise LogoError("The logo must be a PNG or an SVG file.")
    for element in root.iter():
        tag = _local(element.tag)
        if tag in _FORBIDDEN_TAGS:
            raise LogoError(f"The SVG logo uses <{tag}>, which is not allowed.")
        if tag == "style" and _UNSAFE_CSS.search(element.text or ""):
            raise LogoError("The SVG logo loads something from outside the file.")
        for name, value in element.attrib.items():
            attribute = _local(name)
            if attribute.startswith("on"):
                raise LogoError("The SVG logo contains scripting, which is not allowed.")
            if attribute == "href" and not value.startswith("#"):
                raise LogoError("The SVG logo links outside the file, which is not allowed.")
            if attribute == "style" and _UNSAFE_CSS.search(value):
                raise LogoError("The SVG logo loads something from outside the file.")


class LogoStore:
    """Logo files kept in ``<data_dir>/brand/logos``."""

    def __init__(self, data_dir: Path) -> None:
        self.directory = data_dir / "brand" / "logos"

    def save(self, content: bytes) -> str:
        """Check and store a logo and return its stored name."""
        kind = detect_kind(content)
        name = f"{uuid.uuid4().hex}.{kind}"
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / name).write_bytes(content)
        return name

    def path(self, name: str) -> Path:
        """Return the path of a stored logo. Raises :class:`LogoError` for an invalid name."""
        if not _NAME.match(name):
            raise LogoError("Unknown logo file.")
        return self.directory / name

    def exists(self, name: str) -> bool:
        return bool(_NAME.match(name)) and (self.directory / name).is_file()

    def read(self, name: str) -> bytes:
        path = self.path(name)
        if not path.is_file():
            raise LogoError("Unknown logo file.")
        return path.read_bytes()

    def delete(self, name: str | None) -> None:
        """Remove a stored logo; a missing file or ``None`` is ignored."""
        if name and _NAME.match(name):
            (self.directory / name).unlink(missing_ok=True)
