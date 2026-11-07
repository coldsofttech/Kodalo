"""Ask the default AI model once how to lay out the slides of a written post, and keep the answer.

The model never writes text: the copy is already saved, and the slides always show it. It only
chooses, for each slide, a template, its alignment, where a picture sits, an icon and an image,
from what the platform settings allow. With AI-powered templates on it instead writes one shared
stylesheet and a slot layout for each slide (see ``kodalo.core.parsers.html.render``), and
decides where the repo name shows and whether progress marks are drawn. Everything it returns is
checked here: a template or option outside the fixed lists, an icon that is not a Bootstrap Icon,
an image that is not allowed or not available, or a drawing that does not pass the SVG cleaner, is
replaced by the plain default and noted as a warning. When the repository has no icon file and the
designer may use one, the social preview is attached to the same request so the model can say where
the logo is in it.
"""

import json
from dataclasses import asdict, dataclass, fields, replace
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.ai import AiConnections
from kodalo.core.brands.brand import Brand
from kodalo.core.parsers.html.fixed_page import fixed_layout, fixed_style
from kodalo.core.parsers.html.render import (
    MAX_IMAGE_BYTES,
    PROGRESS_STYLES,
    REPO_NAME_PLACES,
    Chrome,
    SlideText,
    brand_tokens,
    build_page,
    clean_css,
    clean_layout,
    icons,
    with_picture,
    with_slots,
)
from kodalo.core.parsers.svg.sanitize import sanitize_svg
from kodalo.core.repositories.ai.parsers import _reply_json, estimate_tokens
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.repositories.service import RepoService
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.platforms import Platforms, PlatformSettings
from kodalo.core.storage import Database
from kodalo.core.storage.models import StudioDesign
from kodalo.core.studio.copy import Choice, CopyAssistant, PostCopy

MAX_OUTPUT_TOKENS = 8000
MAX_HTML_OUTPUT_TOKENS = 16000
IMAGE_TOKENS = 1600  # what an attached image costs, about
TEMPLATES = ("hook", "problem", "step", "proof", "summary", "cta", "image")
ALIGNS = ("left", "center")
MEDIA = ("none", "top", "bottom")
ACCENTS = ("primary", "secondary")
SOURCES = ("none", "social_preview", "repo_icon", "custom_svg")
FITS = ("cover", "contain")
_ROLE_TEMPLATES = {"hook": "hook", "problem": "problem", "step": "step", "proof": "proof"}


@dataclass(frozen=True)
class SlideDesign:
    template: str
    align: str
    media: str
    accent: str
    icon: str
    image_source: str
    image_fit: str
    svg: str
    html: str = ""  # AI-written slide: its cleaned layout, with slots for the copy
    emphasis: str = ""  # a phrase of the headline to set apart


@dataclass(frozen=True)
class Design:
    """How each slide is laid out, and where the logo is in the social preview."""

    platform: str
    idea_id: str
    hook_id: str
    slides: tuple[SlideDesign, ...]
    logo_box: tuple[float, float, float, float] | None
    warnings: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    style: str = ""  # AI-written stylesheet shared by every slide of the post
    repo_name: str = "first_last"  # where the repo name shows: all, first_last, first, last, none
    progress: str = "none"  # progress marks the app draws: dots, bar or none


@dataclass(frozen=True)
class PageAssets:
    """The images a slide page embeds, as (media type, bytes); ``None`` when there is none."""

    social_preview: tuple[str, bytes] | None = None
    repo_icon: tuple[str, bytes] | None = None
    logo_light: tuple[str, bytes] | None = None
    logo_dark: tuple[str, bytes] | None = None


@dataclass(frozen=True)
class DesignPlan:
    """What a run would send and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    items: tuple[str, ...]
    input_tokens: int
    max_output_tokens: int
    sees_social_preview: bool
    writes_html: bool = False  # the AI writes each slide as HTML and CSS


@cache
def _icon_names() -> frozenset[str]:
    return frozenset(icons())


def system_prompt(platform: str, html: bool = False) -> str:
    """The instructions sent to every provider: the platform's bundled designer skill file
    (the one for AI-written HTML slides when ``html``) without its front matter."""
    folder = resources.files("kodalo.core.ai") / "prompts" / "platforms" / platform
    name = f"{platform}-designer-html.SKILL.md" if html else f"{platform}-designer.SKILL.md"
    text = (folder / name).read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def _platform_html(settings: PlatformSettings) -> bool:
    return settings.use_ai_templates


def _limit(html: bool) -> int:
    return MAX_HTML_OUTPUT_TOKENS if html else MAX_OUTPUT_TOKENS


def _pick(value: object, allowed: tuple[str, ...], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _plain(index: int, role: str, single: bool) -> SlideDesign:
    template = "image" if single else _ROLE_TEMPLATES.get(role, "summary" if role else "problem")
    if role == "cta":
        template = "cta"
    return SlideDesign(
        template,
        "center" if template in ("hook", "cta") else "left",
        "none",
        "secondary" if index % 2 else "primary",
        "",
        "none",
        "cover",
        "",
    )


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _box(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        x, y, w, h = (float(value[key]) for key in ("x", "y", "w", "h"))
    except (KeyError, TypeError, ValueError):
        return None
    if min(x, y) < 0 or min(w, h) <= 0.01 or x + w > 1.001 or y + h > 1.001:
        return None
    return (round(x, 4), round(y, 4), round(w, 4), round(h, 4))


def load_image(path: Path, media_type: str) -> tuple[str, bytes] | None:
    """The image at ``path`` for a page, or ``None`` when it cannot be read or is too large."""
    try:
        if path.stat().st_size > MAX_IMAGE_BYTES:
            return None
        return media_type, path.read_bytes()
    except OSError:
        return None


def _design_from_json(payload: str) -> Design:
    data = json.loads(payload)
    box = data["logo_box"]
    known = {f.name for f in fields(SlideDesign)}
    slides = [
        SlideDesign(**{k: v for k, v in slide.items() if k in known}) for slide in data["slides"]
    ]
    if "style" not in data:  # a design from before AI-written slides had a shared style
        slides = [replace(slide, html="") for slide in slides]
    return Design(
        data["platform"],
        data["idea_id"],
        data["hook_id"],
        tuple(slides),
        tuple(box) if box else None,
        tuple(data["warnings"]),
        data["input_tokens"],
        data["output_tokens"],
        data.get("style", ""),
        data.get("repo_name", "first_last"),
        data.get("progress", "none"),
    )


class DesignAssistant:
    """Builds the input for one written post and runs the single AI request."""

    def __init__(
        self,
        copy: CopyAssistant,
        repos: RepoService,
        platforms: Platforms,
        ai: AiConnections,
        database: Database,
    ) -> None:
        self._copy = copy
        self._repos = repos
        self._platforms = platforms
        self._ai = ai
        self._database = database

    def _allowed(self, settings: PlatformSettings, repo_id: str) -> tuple[list[str], bool]:
        """The images the designer may use, and whether to look for the logo in the preview."""
        info = self._repos.get(repo_id)
        preview = self._repos.social_preview(repo_id) is not None
        images: list[str] = []
        if settings.use_social_preview and preview:
            images.append("social_preview")
        look = (
            settings.use_repo_icon and not info.has_icon and preview and not info.icon_box_checked
        )
        # With a logo to find in the preview, the repo icon can be chosen in the same request;
        # it is dropped afterwards if the model finds none.
        if settings.use_repo_icon and (info.has_icon or info.icon_box is not None or look):
            images.append("repo_icon")
        return images, look

    def _request(
        self, choice: Choice, canvas: tuple[int, int]
    ) -> tuple[str, PostCopy, PlatformSettings, list[str], bool]:
        post = self._copy.saved(choice)
        if post is None:
            raise RepoNotFoundError("The copy of this post was not written yet.")
        settings = self._platforms.get(choice.platform)
        images, look = self._allowed(settings, choice.repo_id)
        payload = {
            "product": {"name": self._repos.get(choice.repo_id).name},
            "format": post.format,
            "canvas": {"width": canvas[0], "height": canvas[1]},
            "slides": [{"n": n, **asdict(s)} for n, s in enumerate(post.slides, 1)],
            "allowed": {
                "images": images,
                "icons": settings.use_icons,
                "custom_svg": settings.build_custom_images,
            },
            "added_by_the_app": (
                "the brand logo (or the repo name), the footer text, the slide number and the "
                "progress marks"
            ),
            "look_for_logo": look,
        }
        return json.dumps(payload, ensure_ascii=False, indent=1), post, settings, images, look

    def _preview(self, repo_id: str) -> tuple[str, bytes] | None:
        found = self._repos.social_preview(repo_id)
        if found is None:
            return None
        path, media_type = found
        try:
            return media_type, path.read_bytes()
        except OSError:
            return None

    def plan(self, choice: Choice, canvas: tuple[int, int]) -> DesignPlan:
        """Work out what would be sent and what asking would cost. Nothing is sent."""
        prompt, post, _, _, look = self._request(choice, canvas)
        target = self._ai.default_target()
        html = _platform_html(self._platforms.get(choice.platform))
        tokens = estimate_tokens(system_prompt(choice.platform, html), prompt)
        return DesignPlan(
            target.provider,
            target.label,
            target.model,
            tuple(s.headline for s in post.slides[:1]) or ("the post",),
            tokens + (IMAGE_TOKENS if look else 0),
            min(_limit(html), target.max_tokens or _limit(html)),
            look,
            html,
        )

    def saved(self, choice: Choice) -> Design | None:
        """The design kept for this post, or ``None`` when none was made yet."""
        with self._database.session() as session:
            row = self._row(session, choice)
            return _design_from_json(row.payload) if row is not None else None

    def svg(self, choice: Choice, index: int) -> str | None:
        """The cleaned drawing of one slide, or ``None`` when it has none."""
        design = self.saved(choice)
        if design is None or not 0 <= index < len(design.slides):
            return None
        return design.slides[index].svg or None

    @staticmethod
    def _row(session: Session, choice: Choice) -> StudioDesign | None:
        return session.scalars(
            select(StudioDesign).where(
                StudioDesign.repository_id == choice.repo_id,
                StudioDesign.design_key == choice.key,
            )
        ).first()

    def _save(self, choice: Choice, design: Design) -> None:
        payload = json.dumps(asdict(design), ensure_ascii=False)
        with self._database.session() as session:
            row = self._row(session, choice)
            if row is None:
                session.add(
                    StudioDesign(
                        repository_id=choice.repo_id, design_key=choice.key, payload=payload
                    )
                )
            else:
                row.payload = payload

    def generate(self, choice: Choice, canvas: tuple[int, int]) -> Design:
        """Ask the model once, check and keep its plan and return it. Raises
        ``RepoNotFoundError`` when the copy is missing and ``AiInvalidError`` when the answer is
        not in the expected format."""
        prompt, post, settings, images, look = self._request(choice, canvas)
        preview = self._preview(choice.repo_id) if look else None
        html = _platform_html(settings)
        reply = self._ai.generate(
            system_prompt(choice.platform, html),
            prompt,
            _limit(html),
            purpose="studio",
            title=f"Design for {choice.idea_id} in {choice.repo_id}",
            images=(preview,) if preview else (),
        )
        data = _reply_json(reply.text)
        if not isinstance(data, dict) or not isinstance(data.get("slides"), list):
            raise AiInvalidError(
                "The AI did not answer in the expected format, so there is no design."
            )
        warnings: list[str] = []
        box = _box(data.get("logo_box")) if preview else None
        if look:
            self._repos.save_icon_box(choice.repo_id, box)
        info = self._repos.get(choice.repo_id)
        box = box or info.icon_box
        logo = info.has_icon or box is not None
        style = ""
        place = "first_last"
        progress = "none"
        if html:
            slides, style = self._html_slides(data, post, settings, images, logo, warnings)
            place = _pick(data.get("repo_name"), REPO_NAME_PLACES, "first_last")
            progress = _pick(data.get("progress"), PROGRESS_STYLES, "none")
        else:
            slides = self._slides(data["slides"], post, settings, images, logo, warnings)
            if images and not any(s.image_source != "none" for s in slides):
                warnings.append(
                    "The AI used none of the pictures you allowed. Refresh with AI to try again."
                )
        design = Design(
            choice.platform,
            post.idea_id,
            post.hook_id,
            slides,
            box,
            tuple(warnings),
            reply.input_tokens,
            reply.output_tokens,
            style,
            place,
            progress,
        )
        self._save(choice, design)
        return design

    @staticmethod
    def _html_slides(
        data: dict[str, Any],
        post: PostCopy,
        settings: PlatformSettings,
        images: list[str],
        logo: bool,
        warnings: list[str],
    ) -> tuple[tuple[SlideDesign, ...], str]:
        """Check the AI's shared stylesheet and each slide's layout. A layout that fails keeps
        its fixed-template design, so a post is never left without a slide. The app puts the
        words in the slots itself, so a slide always shows the copy and nothing else."""
        single = post.format == "single_image"
        plain = tuple(_plain(i, s.role, single) for i, s in enumerate(post.slides))
        style = clean_css(str(data.get("style") or ""))
        if style is None:
            warnings.append(
                "The AI's stylesheet was not used because it is empty, too large, uses "
                "!important or loads something; the fixed templates are used."
            )
            return plain, ""
        assets = {a for a in images if a != "repo_icon" or logo}
        raw = data.get("slides")
        answered: list[Any] = raw if isinstance(raw, list) else []
        result: list[SlideDesign] = []
        pictures = icon_count = 0
        for index, slide in enumerate(post.slides):
            item = _dict(answered[index]) if index < len(answered) else {}
            try:
                layout = clean_layout(
                    str(item.get("layout") or item.get("html") or ""),
                    assets,
                    allow_icons=settings.use_icons,
                    allow_svg=settings.build_custom_images,
                )
            except ValueError as reason:
                warnings.append(
                    f"Slide {index + 1}: the AI's layout was not used because {reason}; "
                    "the fixed template is used."
                )
                result.append(plain[index])
                continue
            pictures += layout.pictures
            icon_count += layout.icons
            phrase = str(item.get("accent") or "").strip()[:120]
            result.append(
                replace(
                    plain[index],
                    html=with_slots(layout, body=bool(slide.body)),
                    emphasis=phrase if phrase.casefold() in slide.headline.casefold() else "",
                )
            )
            if len(slide.headline) > 140 or len(slide.body) > 220:
                warnings.append(f"Slide {index + 1}: its text is long and may not fit.")
        if assets and not pictures:
            first = next((i for i, s in enumerate(result) if s.html), None)
            if first is not None:
                asset = "social_preview" if "social_preview" in assets else "repo_icon"
                result[first] = replace(result[first], html=with_picture(result[first].html, asset))
                warnings.append(
                    f"The AI used none of the pictures you allowed, so the app added the "
                    f"{asset.replace('_', ' ')} to slide {first + 1}."
                )
        if settings.use_icons and not icon_count and any(s.html for s in result):
            warnings.append(
                "The AI used no icons although icons are on. Refresh with AI to try again."
            )
        return tuple(result), style

    def slide_page(
        self,
        choice: Choice,
        index: int,
        brand: Brand,
        mode: str,
        assets: PageAssets,
    ) -> str | None:
        """The page of one slide in the brand's colors for ``mode`` (``light`` or ``dark``), with
        every picture and the logo embedded: the AI's layout when it wrote one, else the fixed
        template's. ``None`` when the post has no saved design or no such slide. When the brand has
        no logo, the repo name stands in its place."""
        design = self.saved(choice)
        post = self._copy.saved(choice)
        if design is None or post is None or not 0 <= index < len(design.slides):
            return None
        slide = design.slides[index]
        if index >= len(post.slides):
            return None
        pick = "dark" if mode == "dark" else "light"
        colors = {
            name: getattr(getattr(brand.data.colors, name), pick)
            for name in type(brand.data.colors).model_fields
        }
        fonts = {
            name: getattr(brand.data.fonts, name).family
            for name in type(brand.data.fonts).model_fields
        }
        total = len(design.slides)
        last = index == total - 1
        logo = brand.data.logo
        variant = "dark" if pick == "dark" and logo.dark_file else "light"
        file = logo.dark_file if variant == "dark" else logo.file
        bytes_ = assets.logo_dark if variant == "dark" else assets.logo_light
        shown = logo.show_on == "all" or (
            (logo.show_on == "first" and index == 0) or (logo.show_on == "last" and last)
        )
        name = self._repos.get(choice.repo_id).name
        wordmark = name if shown and not (file and bytes_) else ""
        named = {
            "all": True,
            "first_last": index == 0 or last,
            "first": index == 0,
            "last": last,
        }.get(design.repo_name, False)
        copy = post.slides[index]
        chrome = Chrome(
            bytes_ if shown and file else None,
            wordmark,
            logo.position,
            logo.size_percent,
            logo.padding,
            brand.layout.footer_text,
            name if named and not wordmark else "",
            f"{index + 1}/{total}" if brand.layout.slide_numbers else "",
            brand.layout.margin_side,
            brand.layout.margin_bottom,
            design.progress,
            index,
            total,
        )
        written = bool(slide.html and design.style)
        density = {"compact": 18, "regular": 30, "spacious": 46}.get(brand.layout.density, 30)
        return build_page(
            slide.html if written else fixed_layout(slide, index),
            design.style
            if written
            else fixed_style(
                slide,
                margins=(
                    brand.layout.margin_top,
                    brand.layout.margin_side,
                    brand.layout.margin_bottom,
                ),
                radius=brand.layout.corner_radius,
                gap=density,
            ),
            SlideText(copy.headline, copy.body, copy.alt_text, slide.emphasis),
            tokens=brand_tokens(colors, fonts),
            canvas=(brand.canvas.width, brand.canvas.height),
            images={"social_preview": assets.social_preview, "repo_icon": assets.repo_icon},
            box=design.logo_box,
            chrome=chrome,
        )

    @staticmethod
    def _slides(
        answered: list[Any],
        post: PostCopy,
        settings: PlatformSettings,
        images: list[str],
        logo: bool,
        warnings: list[str],
    ) -> tuple[SlideDesign, ...]:
        single = post.format == "single_image"
        icons = _icon_names()
        result: list[SlideDesign] = []
        for index, slide in enumerate(post.slides):
            plain = _plain(index, slide.role, single)
            item: dict[str, Any] = (
                answered[index]
                if index < len(answered) and isinstance(answered[index], dict)
                else {}
            )
            if not item:
                warnings.append(
                    f"The AI gave no design for slide {index + 1}; the plain one is used."
                )
            image = _dict(item.get("image"))
            source = _pick(image.get("source"), SOURCES, "none")
            svg = ""
            if source == "custom_svg":
                if settings.build_custom_images:
                    svg = sanitize_svg(str(image.get("svg") or "")) or ""
                if not svg:
                    source = "none"
                    warnings.append(f"Slide {index + 1}: the drawing was not allowed or not safe.")
            elif source in ("social_preview", "repo_icon") and (
                source not in images or (source == "repo_icon" and not logo)
            ):
                warnings.append(
                    f"Slide {index + 1}: the {source.replace('_', ' ')} is not available."
                )
                source = "none"
            icon = str(item.get("icon") or "").removeprefix("bi-")
            if icon and not (settings.use_icons and icon in icons):
                if settings.use_icons:
                    warnings.append(f"Slide {index + 1}: {icon} is not a Bootstrap icon.")
                icon = ""
            media = _pick(item.get("media"), MEDIA, "none")
            if source != "none" and media == "none":
                media = "top"
            result.append(
                SlideDesign(
                    "image" if single else _pick(item.get("template"), TEMPLATES, plain.template),
                    _pick(item.get("align"), ALIGNS, plain.align),
                    media if source != "none" else "none",
                    _pick(item.get("accent"), ACCENTS, plain.accent),
                    icon,
                    source,
                    _pick(image.get("fit"), FITS, "cover"),
                    svg,
                )
            )
        return tuple(result)
