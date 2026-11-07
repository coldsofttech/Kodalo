"""Slides laid out by a fixed template, as the same kind of page the AI-written slides use.

A fixed template (hook, problem, step, proof, summary, image or cta) is turned into a layout and a
stylesheet that ``render.build_page`` fills with the saved copy, so the preview in the window
and the picture that is posted come from one page. The look follows the template, the alignment,
the accent, the picture and the icon the design plan chose.
"""

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kodalo.core.studio.design import SlideDesign

_ALT_TEMPLATES = ("cta",)


def fixed_layout(slide: "SlideDesign", index: int) -> str:
    """The layout of a fixed-template slide: boxes with slots for the headline and the body."""
    classes = f"fx-slide fx-{slide.align} fx-{slide.accent} fx-t-{slide.template}"
    media = _media(slide)
    parts = [f'<div class="{classes}"><div class="fx-body">']
    if slide.media == "top":
        parts.append(media)
    if slide.template == "step":
        parts.append(f'<span class="fx-badge">{index + 1}</span>')
    if slide.icon:
        parts.append(f'<i data-icon="{slide.icon}" class="fx-icon"></i>')
    parts.append('<h1 data-slot="headline" class="fx-title"></h1>')
    parts.append('<p data-slot="body" class="fx-text"></p>')
    if slide.media == "bottom":
        parts.append(media)
    parts.append("</div></div>")
    return "".join(parts)


def _media(slide: "SlideDesign") -> str:
    if slide.image_source in ("social_preview", "repo_icon"):
        kind = "fx-icon-box" if slide.image_source == "repo_icon" else f"fx-fit-{slide.image_fit}"
        return f'<div class="fx-media {kind}"><img data-asset="{slide.image_source}"></div>'
    if slide.image_source == "custom_svg" and slide.svg:
        return '<div class="fx-media"><span class="fx-drawing"></span></div>'
    return ""


def fixed_style(
    slide: "SlideDesign",
    *,
    margins: tuple[int, int, int],
    radius: int,
    gap: int,
) -> str:
    """The stylesheet of a fixed-template slide. ``margins`` are the top, side and bottom margins
    in canvas pixels."""
    top, side, bottom = margins
    alt = slide.template in _ALT_TEMPLATES
    title = "var(--b-secondary)" if slide.accent == "secondary" else "var(--b-primary)"
    if alt:
        title = "var(--b-text-alt)"
    title_size = 96 if slide.template == "hook" else 80
    rule = (
        ".fx-t-problem .fx-title,.fx-t-summary .fx-title{padding-bottom:20px;"
        "border-bottom:6px solid var(--b-secondary)}"
        if slide.template in ("problem", "summary")
        else ""
    )
    css = (
        ".kodalo-root{"
        + (
            "background:var(--b-background-alt);color:var(--b-text-alt);"
            if alt
            else "background:var(--b-background);"
        )
        + "}"
        f".fx-slide{{display:flex;width:100%;height:100%;padding:{top}px {side}px "
        f"{bottom + 40}px;font-size:38px;line-height:1.35}}"
        f".fx-body{{display:grid;gap:{gap}px;align-content:center;flex:1;min-width:0}}"
        ".fx-left,.fx-left .fx-body{text-align:left;justify-items:start}"
        ".fx-center,.fx-center .fx-body{text-align:center;justify-items:center}"
        f".fx-title{{margin:0;font-size:{title_size}px;line-height:1.1;color:{title}}}"
        ".fx-text{margin:0}.fx-text:empty{display:none}"
        f"{rule}"
        ".fx-badge{display:grid;place-items:center;width:96px;height:96px;border-radius:50%;"
        f"background:{'var(--b-secondary)' if slide.accent == 'secondary' else 'var(--b-primary)'};"
        "color:var(--b-background);font-family:var(--f-heading);font-size:52px;font-weight:700}"
        f".fx-icon{{font-size:120px;line-height:1;color:{title}}}"
        f".fx-media{{width:100%;overflow:hidden;border-radius:{radius}px}}"
        ".fx-media img{display:block;width:100%;height:480px;object-fit:cover}"
        ".fx-fit-contain img{object-fit:contain}"
        ".fx-t-proof .fx-media{border:6px solid var(--b-primary)}"
        ".fx-icon-box{width:260px;height:260px}"
        ".fx-icon-box img{height:100%;object-fit:contain}"
        ".fx-media .kodalo-crop{width:100%}"
    )
    if slide.image_source == "custom_svg" and slide.svg:
        data = base64.b64encode(slide.svg.encode("utf-8")).decode("ascii")
        mask = f'url("data:image/svg+xml;base64,{data}") center / contain no-repeat'
        css += (
            ".fx-drawing{display:block;width:100%;height:420px;"
            f"background-color:{title if not alt else 'var(--b-primary)'};"
            f"-webkit-mask:{mask};mask:{mask}}}"
        )
    return css
