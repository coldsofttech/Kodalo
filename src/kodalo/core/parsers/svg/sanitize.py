"""Make an SVG written by the AI safe to show: plain shapes and text only.

Only a short list of drawing elements and attributes is kept. Scripts, links, images, styles,
event handlers, external references and DOCTYPE or entity tricks are never kept, so a drawing can
neither run code nor fetch anything. A drawing that is too large, not well formed or empty after
cleaning is refused. Colors are kept as written, since the AI is told to use the brand's.
"""

import re
import xml.etree.ElementTree as ET

MAX_SVG_BYTES = 20_000
_NS = "http://www.w3.org/2000/svg"
_ELEMENTS = {
    "svg",
    "g",
    "defs",
    "title",
    "desc",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
}
_ATTRIBUTES = {
    "viewBox",
    "width",
    "height",
    "preserveAspectRatio",
    "x",
    "y",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "x1",
    "x2",
    "y1",
    "y2",
    "d",
    "points",
    "transform",
    "fill",
    "fill-opacity",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "opacity",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientUnits",
    "gradientTransform",
    "id",
    "clip-path",
    "font-size",
    "font-family",
    "font-weight",
    "text-anchor",
    "dominant-baseline",
}
_URL = re.compile(r"url\(\s*([^)]*)\)", re.IGNORECASE)
_SAFE_VALUE = re.compile(r"^[\w\s.,#%()+\-:'\"]*$")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _safe_value(value: str) -> bool:
    if not _SAFE_VALUE.match(value):
        return False
    return all(ref.strip().strip("'\"").startswith("#") for ref in _URL.findall(value))


def _clean(element: ET.Element) -> ET.Element | None:
    name = _local(element.tag)
    if name not in _ELEMENTS:
        return None
    kept = ET.Element(f"{{{_NS}}}{name}")
    for key, value in element.attrib.items():
        if key in _ATTRIBUTES and _safe_value(value):
            kept.set(key, value)
    if name in ("text", "tspan", "title", "desc"):
        kept.text = (element.text or "")[:200]
    for child in element:
        cleaned = _clean(child)
        if cleaned is not None:
            kept.append(cleaned)
            cleaned.tail = None
    return kept


def sanitize_svg(markup: str) -> str | None:
    """Return the cleaned SVG, or ``None`` when it is too large, not well formed, not an ``svg``
    element or has nothing left to draw."""
    if not markup or len(markup.encode("utf-8")) > MAX_SVG_BYTES:
        return None
    if re.search(r"<!(DOCTYPE|ENTITY)", markup, re.IGNORECASE):
        return None
    try:
        root = ET.fromstring(markup.strip())  # noqa: S314 - DOCTYPE and entities are refused above
    except ET.ParseError:
        return None
    if _local(root.tag) != "svg":
        return None
    cleaned = _clean(root)
    if cleaned is None or len(cleaned) == 0:
        return None
    if "viewBox" not in cleaned.attrib:
        return None
    ET.register_namespace("", _NS)
    return ET.tostring(cleaned, encoding="unicode")
