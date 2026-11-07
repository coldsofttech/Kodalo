"""Slides whose layout the AI wrote: make it safe, fill the slots, and build a self-contained page.

The AI writes one stylesheet for the whole post and, for each slide, a layout made of plain boxes
with *slots*: ``<h1 data-slot="headline">``, ``<p data-slot="body">``, ``<img data-asset="...">``
and ``<i data-icon="...">``. It never writes text. The app keeps only layout elements and class
names, drops every other word, and fills the slots itself with the saved copy under a fixed type
scale, so a slide always shows the copy and nothing else, and every slide of a post is sized the
same. The brand's logo (or the repo name when there is none), the footer, the slide number and the
progress marks are drawn by the app, so they are identical on every slide. Pictures and the logo are
embedded in the page as data, so the page loads nothing: it is shown in a sandboxed frame, which
cannot send the window's login to the API. The stylesheet may not load anything or use
``!important``. A layout that draws a diagram out of empty boxes is refused unless custom images
are allowed.
"""

import base64
import html
import json
import re
from dataclasses import dataclass
from functools import cache
from html.parser import HTMLParser
from importlib import resources

from kodalo.core.parsers.svg.sanitize import _ATTRIBUTES as _SVG_ATTRIBUTES
from kodalo.core.parsers.svg.sanitize import _ELEMENTS as _SVG_ELEMENTS
from kodalo.core.parsers.svg.sanitize import _safe_value

MAX_HTML_BYTES = 12_000
MAX_CSS_BYTES = 12_000
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_DECORATIONS = 3  # empty boxes a layout may use (rules, bars) without custom images
ASSETS = ("social_preview", "repo_icon")
REPO_NAME_PLACES = ("all", "first_last", "first", "last", "none")
PROGRESS_STYLES = ("dots", "bar", "none")
_SLOTS = ("headline", "body")
_SLOT_TAGS = {"h1", "h2", "h3", "h4", "p", "div", "span"}
_BOXES = {"div", "span", "section", "header", "footer"}
_DROP_WITH_CONTENT = {
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "noscript",
    "template",
    "head",
    "title",
    "form",
    "textarea",
    "select",
    "button",
    "audio",
    "video",
    "canvas",
}
_DROP_VOID = {"link", "meta", "input", "source", "track", "base"}
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_CLASS = re.compile(r"^[A-Za-z][\w-]*$")
_SVG_LOWER = {n.lower(): n for n in _SVG_ELEMENTS if n not in ("text", "tspan", "title", "desc")}
_SVG_ATTR_LOWER = {n.lower(): n for n in _SVG_ATTRIBUTES if not n.startswith("font")}
_FORBIDDEN_CSS = re.compile(r"@|url\s*\(|expression|javascript|behavio|binding|\\|<|>|import", re.I)
_IMPORTANT = re.compile(r"!\s*important", re.I)
_SLOT = re.compile(
    r'<(h1|h2|h3|h4|p|div|span) data-slot="(headline|body)"((?: class="[^"]*")?)></\1>'
)
_ICON = re.compile(r'<i data-icon="([a-z0-9-]+)"((?: class="[^"]*")?)></i>')
_IMG = re.compile(r'<img data-asset="([a-z_]+)"((?: class="[^"]*")?)>')
_FAMILY = re.compile(r"[^\w \-]")
_CLASS_ATTR = len(' class="')


@cache
def icons() -> dict[str, str]:
    """Every Bootstrap Icons icon: its name and the inside of its 16 x 16 drawing."""
    text = (resources.files("kodalo.core.studio") / "icons.json").read_text("utf-8")
    data: dict[str, str] = json.loads(text)
    return data


@dataclass(frozen=True)
class Layout:
    """A cleaned layout and what it holds."""

    html: str
    headline: bool
    body: bool
    decorations: int
    icons: int
    pictures: int


class _Cleaner(HTMLParser):
    def __init__(self, assets: set[str], allow_icons: bool, allow_svg: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.assets = assets
        self.allow_icons = allow_icons
        self.allow_svg = allow_svg
        self.out: list[str] = []
        self.open: list[str] = []  # what each open element closes with
        self.kids: list[int] = []
        self.skip = 0
        self.skip_tag = ""
        self.slot_depth = 0
        self.slot_tag = ""
        self.in_svg = 0
        self.slots: set[str] = set()
        self.decorations = 0
        self.icons = 0
        self.pictures = 0

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> str:
        value = dict(attrs).get("class") or ""
        names = [n for n in value.split() if _CLASS.match(n)]
        return f' class="{" ".join(names)}"' if names else ""

    @staticmethod
    def _svg_attrs(attrs: list[tuple[str, str | None]]) -> str:
        kept = []
        for key, value in attrs:
            name = _SVG_ATTR_LOWER.get(key)
            if name and _safe_value(value or ""):
                kept.append(f'{name}="{html.escape(value or "", quote=True)}"')
        return (" " + " ".join(kept)) if kept else ""

    def _child(self) -> None:
        if self.kids:
            self.kids[-1] += 1

    # -- parser events --

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROP_VOID:
            return
        if self.skip:
            if tag == self.skip_tag:
                self.skip += 1
            return
        if self.slot_depth:
            if tag == self.slot_tag:
                self.slot_depth += 1
            return
        if tag in _DROP_WITH_CONTENT or (tag == "svg" and not self.allow_svg):
            self.skip, self.skip_tag = 1, tag
            return
        if self.in_svg or tag == "svg":
            self._svg_start(tag, attrs)
            return
        slot = dict(attrs).get("data-slot")
        if tag in _SLOT_TAGS and slot in _SLOTS:
            self._child()
            self.slots.add(str(slot))
            self.out.append(f'<{tag} data-slot="{slot}"{self._classes(attrs)}></{tag}>')
            self.slot_depth, self.slot_tag = 1, tag
            return
        if tag == "i":
            self._icon(attrs)
            return
        if tag == "img":
            asset = dict(attrs).get("data-asset") or ""
            if asset in self.assets:
                self._child()
                self.pictures += 1
                self.out.append(f'<img data-asset="{asset}"{self._classes(attrs)}>')
            return
        if tag in _BOXES:
            self._child()
            self.out.append(f"<{tag}{self._classes(attrs)}>")
            self.open.append(tag)
            self.kids.append(0)

    def _icon(self, attrs: list[tuple[str, str | None]]) -> None:
        name = dict(attrs).get("data-icon") or ""
        classes = [n for n in (dict(attrs).get("class") or "").split() if n]
        if not name:  # tolerate the Bootstrap Icons class form, ``bi bi-git``
            name = next((n[3:] for n in classes if n.startswith("bi-")), "")
        if self.allow_icons and _NAME.match(name) and name in icons():
            self._child()
            self.icons += 1
            kept = [n for n in classes if _CLASS.match(n) and n != "bi" and not n.startswith("bi-")]
            extra = f' class="{" ".join(kept)}"' if kept else ""
            self.out.append(f'<i data-icon="{name}"{extra}></i>')
        self.slot_depth, self.slot_tag = 1, "i"

    def _svg_start(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = _SVG_LOWER.get(tag)
        if name is None:
            self.skip, self.skip_tag = 1, tag
            return
        if name == "svg":
            self._child()
            self.in_svg += 1
        self.out.append(f"<{name}{self._svg_attrs(attrs)}>")
        self.open.append(f"svg:{name}")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROP_VOID or tag in _DROP_WITH_CONTENT or self.skip or self.slot_depth:
            return
        self.handle_starttag(tag, attrs)
        if tag in _BOXES or self.in_svg or tag in _SVG_LOWER:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.skip:
            if tag == self.skip_tag:
                self.skip -= 1
            return
        if self.slot_depth:
            if tag == self.slot_tag:
                self.slot_depth -= 1
            return
        if not self.open:
            return
        top = self.open.pop()
        if top.startswith("svg:"):
            self.out.append(f"</{top[4:]}>")
            if top == "svg:svg":
                self.in_svg -= 1
            return
        self.out.append(f"</{top}>")
        if self.kids and self.kids.pop() == 0:
            self.decorations += 1

    def handle_data(self, data: str) -> None:
        """No text is kept: the words of a slide come from its copy, in the slots."""

    def close_all(self) -> None:
        while self.open:
            self.handle_endtag(self.open[-1].removeprefix("svg:"))


def clean_css(css: str) -> str | None:
    """The stylesheet without comments, or ``None`` when it is empty, too large, uses
    ``!important`` or could load or run anything."""
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S).strip()
    if not stripped or len(stripped.encode("utf-8")) > MAX_CSS_BYTES:
        return None
    if _FORBIDDEN_CSS.search(stripped) or _IMPORTANT.search(stripped):
        return None
    return stripped


def clean_layout(markup: str, assets: set[str], *, allow_icons: bool, allow_svg: bool) -> Layout:
    """Return the cleaned layout of one slide. Raises ``ValueError`` with a plain reason when it
    must not be used: too large, empty, or a diagram drawn out of empty boxes while custom images
    are not allowed."""
    if len(markup.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("it is too large")
    cleaner = _Cleaner(assets, allow_icons, allow_svg)
    cleaner.feed(markup)
    cleaner.close()
    cleaner.close_all()
    cleaned = "".join(cleaner.out).strip()
    if not cleaned:
        raise ValueError("it has nothing to show")
    if not allow_svg and cleaner.decorations > MAX_DECORATIONS:
        raise ValueError(
            "it draws a diagram out of empty boxes, which needs Build custom images in Settings"
        )
    return Layout(
        cleaned,
        "headline" in cleaner.slots,
        "body" in cleaner.slots,
        cleaner.decorations,
        cleaner.icons,
        cleaner.pictures,
    )


def with_slots(layout: Layout, *, body: bool) -> str:
    """The layout with a headline slot (and a body slot when the slide has a body) added at the
    end of its outer box when the AI left one out, so the copy always shows."""
    missing = ""
    if not layout.headline:
        missing += '<h1 data-slot="headline"></h1>'
    if body and not layout.body:
        missing += '<p data-slot="body"></p>'
    if not missing:
        return layout.html
    end = layout.html.rfind("</")
    if end < 0:
        return layout.html + missing
    return layout.html[:end] + missing + layout.html[end:]


def with_picture(markup: str, asset: str) -> str:
    """The layout with a picture added at the top of its outer box."""
    picture = f'<img data-asset="{asset}" class="kodalo-auto">'
    found = re.search(r"<[a-z][^>]*>", markup)
    if found is None:
        return picture + markup
    return markup[: found.end()] + picture + markup[found.end() :]


@dataclass(frozen=True)
class Chrome:
    """What the app draws on every slide itself: the brand logo, or the repo name as a wordmark
    when there is none, the footer, the slide number and the progress marks."""

    logo: tuple[str, bytes] | None  # media type and bytes of the logo to show, if any
    wordmark: str  # shown in the logo's place when the brand has no logo
    logo_position: str
    logo_percent: int
    logo_padding: int
    footer_text: str
    repo_name: str  # shown in the footer on this slide; empty when not
    slide_number: str  # for example ``2/5``, or empty
    margin_side: int
    margin_bottom: int
    progress: str = "none"  # dots, bar or none
    index: int = 0
    total: int = 1


@dataclass(frozen=True)
class SlideText:
    """What a slide says: the copy's, never the AI's."""

    headline: str
    body: str
    alt: str
    emphasis: str = ""  # a phrase of the headline to set apart


_SPOTS = {
    "top_left": "top:{p}px;left:{p}px",
    "top_center": "top:{p}px;left:50%;translate:-50% 0",
    "top_right": "top:{p}px;right:{p}px",
    "bottom_left": "bottom:{p}px;left:{p}px",
    "bottom_center": "bottom:{p}px;left:50%;translate:-50% 0",
    "bottom_right": "bottom:{p}px;right:{p}px",
}


def _uri(media_type: str, data: bytes) -> str:
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


def _emphasized(text: str, phrase: str) -> str:
    safe = html.escape(text, quote=False)
    start = text.casefold().find(phrase.casefold()) if phrase else -1
    if start < 0:
        return safe
    end = start + len(phrase)
    return (
        f"{html.escape(text[:start], quote=False)}"
        f'<span class="kodalo-accent">{html.escape(text[start:end], quote=False)}</span>'
        f"{html.escape(text[end:], quote=False)}"
    )


def type_scale(headline: str, body: str, width: int) -> str:
    """The fixed type scale for a canvas ``width`` pixels wide (written for 1080): the headline
    shrinks with its length, and the body never goes below 34 pixels."""
    factor = width / 1080
    if len(headline) <= 30:
        big = 96
    elif len(headline) <= 60:
        big = 76
    elif len(headline) <= 90:
        big = 60
    else:
        big = 52
    small = 38 if len(body) <= 80 else 34
    return (
        f".kodalo-headline{{font-family:var(--f-heading)!important;"
        f"font-size:{round(big * factor)}px!important;line-height:1.2!important}}"
        f".kodalo-body{{font-family:var(--f-body)!important;"
        f"font-size:{round(small * factor)}px!important;line-height:1.4!important}}"
    )


def _progress(chrome: Chrome, factor: float) -> tuple[str, str]:
    """The progress marks, drawn the same way on every slide: only the current one changes."""
    if chrome.progress == "none" or chrome.total < 2:
        return "", ""
    marks = "".join(
        f'<span class="{"on" if n == chrome.index else "done" if n < chrome.index else ""}"></span>'
        for n in range(chrome.total)
    )
    markup = (
        f'<div class="kodalo-progress kodalo-{chrome.progress}" role="img" '
        f'aria-label="Slide {chrome.index + 1} of {chrome.total}">{marks}</div>'
    )
    bottom = max(chrome.margin_bottom // 2, 24) + round(64 * factor)
    css = (
        f".kodalo-progress{{position:absolute!important;left:{chrome.margin_side}px!important;"
        f"right:{chrome.margin_side}px!important;bottom:{bottom}px!important;"
        "display:flex!important;z-index:2!important}"
        ".kodalo-progress span{background:var(--b-text)!important;opacity:.25!important}"
        ".kodalo-progress span.done{background:var(--b-primary)!important;opacity:1!important}"
        ".kodalo-progress span.on{background:var(--b-secondary)!important;opacity:1!important}"
    )
    if chrome.progress == "dots":
        size = round(22 * factor)
        css += (
            f".kodalo-dots{{gap:{round(26 * factor)}px!important;"
            "justify-content:center!important}"
            f".kodalo-dots span{{width:{size}px!important;height:{size}px!important;"
            "border-radius:50%!important}"
        )
    else:
        css += (
            f".kodalo-bar{{gap:{round(10 * factor)}px!important}}"
            f".kodalo-bar span{{flex:1!important;height:{round(10 * factor)}px!important;"
            f"border-radius:{round(5 * factor)}px!important}}"
        )
    return markup, css


def _chrome(chrome: Chrome, width: int) -> tuple[str, str]:
    """The extra HTML and CSS for the logo or wordmark, the progress marks and the footer."""
    factor = width / 1080
    markup, css = _progress(chrome, factor)
    spot = _SPOTS.get(chrome.logo_position, _SPOTS["top_left"]).format(p=chrome.logo_padding)
    if chrome.logo:
        markup += f'<img class="kodalo-logo" src="{_uri(*chrome.logo)}" alt="">'
        css += (
            f".kodalo-logo{{position:absolute!important;{spot};z-index:2;height:auto;"
            f"max-height:30%;width:{round(width * chrome.logo_percent / 100)}px;"
            "object-fit:contain}"
        )
    elif chrome.wordmark:
        markup += f'<span class="kodalo-wordmark">{html.escape(chrome.wordmark)}</span>'
        css += (
            f".kodalo-wordmark{{position:absolute!important;{spot};z-index:2;"
            "font-family:var(--f-heading);font-weight:700;color:var(--b-primary);"
            f"font-size:{round(40 * factor)}px;line-height:1}}"
        )
    left = " · ".join(part for part in (chrome.repo_name, chrome.footer_text) if part)
    if left or chrome.slide_number:
        start = chrome.logo_position == "bottom_right"
        markup += (
            '<footer class="kodalo-footer">'
            f"<span>{html.escape(left)}</span><span>{html.escape(chrome.slide_number)}</span>"
            "</footer>"
        )
        css += (
            f".kodalo-footer{{position:absolute!important;z-index:2;left:{chrome.margin_side}px;"
            f"right:{chrome.margin_side}px;bottom:{max(chrome.margin_bottom // 2, 24)}px;"
            f"display:flex;gap:24px;font-size:{round(26 * factor)}px;opacity:.8;"
            f"justify-content:{'flex-start' if start else 'space-between'}}}"
        )
    return markup, css


def _crop(uri: str, alt: str, box: tuple[float, float, float, float], extra: str) -> str:
    x, y, w, h = box
    classes = f"kodalo-crop {extra}".strip()
    return (
        f'<span class="{classes}" role="img" aria-label="{alt}" '
        f'data-box="{x:.4f} {y:.4f} {w:.4f} {h:.4f}"><img src="{uri}" alt=""></span>'
    )


def _extra(classes: str) -> str:
    return classes[_CLASS_ATTR:-1] if classes else ""


def build_page(
    layout: str,
    style: str,
    text: SlideText,
    *,
    tokens: dict[str, str],
    canvas: tuple[int, int],
    images: dict[str, tuple[str, bytes] | None],
    box: tuple[float, float, float, float] | None,
    chrome: Chrome | None = None,
) -> str:
    """The page of one slide, with nothing to load: the brand's tokens as CSS variables, the
    shared stylesheet, the layout with its slots filled by the copy under the fixed type scale,
    the pictures and icons embedded, and what the app draws itself."""
    width, height = canvas
    alt = html.escape(text.alt, quote=True)

    def slot(match: re.Match[str]) -> str:
        tag, name, classes = match.groups()
        value = text.headline if name == "headline" else text.body
        inner = _emphasized(value, text.emphasis if name == "headline" else "")
        names = f"kodalo-{name} {_extra(classes)}".strip()
        return f'<{tag} class="{names}">{inner}</{tag}>'

    def icon(match: re.Match[str]) -> str:
        inner = icons().get(match.group(1), "")
        names = f"kodalo-icon {_extra(match.group(2))}".strip()
        return (
            f'<svg class="{names}" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">'
            f"{inner}</svg>"
        )

    def picture(match: re.Match[str]) -> str:
        asset, classes = match.groups()
        extra = _extra(classes)
        found = images.get(asset)
        preview = images.get("social_preview")
        if asset == "repo_icon" and found is None and box and preview:
            return _crop(_uri(*preview), alt, box, extra)
        if found is None:
            return ""
        klass = f' class="{extra}"' if extra else ""
        return f'<img{klass} src="{_uri(*found)}" alt="{alt}">'

    body = _IMG.sub(picture, _ICON.sub(icon, _SLOT.sub(slot, layout)))
    extra_markup, extra_css = _chrome(chrome, width) if chrome else ("", "")
    variables = "".join(f"{name}:{value};" for name, value in tokens.items())
    crop = ""
    if box:
        x, y, w, h = box
        crop = (
            f".kodalo-crop{{--w:{w:.4f};--h:{h:.4f};--x:{x:.4f};--y:{y:.4f};"
            "position:relative;display:block;overflow:hidden;aspect-ratio:1}"
            ".kodalo-crop img{position:absolute;max-width:none;width:calc(100%/var(--w));"
            "height:auto;left:calc(-100%*var(--x)/var(--w));top:calc(-100%*var(--y)/var(--h))}"
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Slide</title><style>'
        f":root{{{variables}}}"
        f"html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden}}"
        "body{position:relative;background:var(--b-background);color:var(--b-text);"
        "font-family:var(--f-body)}"
        "*{box-sizing:border-box}"
        ".kodalo-root{position:relative;width:100%;height:100%}"
        ".kodalo-accent{color:var(--b-primary)}"
        ".kodalo-icon{width:1em;height:1em;font-size:120px;vertical-align:-.125em}"
        f".kodalo-auto{{display:block;width:100%;height:{round(height * 0.3)}px;"
        "object-fit:cover;border-radius:24px}"
        f"{crop}"
        f"{style}"
        f"{type_scale(text.headline, text.body, width)}"
        f"{extra_css}"
        f'</style></head><body><div class="kodalo-root">{body}{extra_markup}</div></body></html>'
    )


def _family(name: str) -> str:
    return _FAMILY.sub("", name)[:64]


def brand_tokens(colors: dict[str, str], fonts: dict[str, str]) -> dict[str, str]:
    """CSS variables for the brand: ``--b-<color>`` (underscores become dashes) and ``--f-<font>``
    with a generic fallback."""
    tokens = {f"--b-{name.replace('_', '-')}": value for name, value in colors.items()}
    for name, family in fonts.items():
        generic = "monospace" if name.startswith("mono") else "sans-serif"
        tokens[f"--f-{name.replace('_', '-')}"] = f'"{_family(family)}", {generic}'
    return tokens
