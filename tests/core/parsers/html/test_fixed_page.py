import pytest

from kodalo.core.parsers.html.fixed_page import fixed_layout, fixed_style
from kodalo.core.parsers.html.render import SlideText, build_page
from kodalo.core.studio.design import SlideDesign

MARGINS = (96, 80, 96)


def _slide(**changes: str) -> SlideDesign:
    plan = {
        "template": "step",
        "align": "left",
        "media": "none",
        "accent": "primary",
        "icon": "",
        "image_source": "none",
        "image_fit": "cover",
        "svg": "",
    }
    return SlideDesign(**{**plan, **changes})


def _page(slide: SlideDesign, index: int = 0, body: str = "More") -> str:
    return build_page(
        fixed_layout(slide, index),
        fixed_style(slide, margins=MARGINS, radius=24, gap=30),
        SlideText("Headline", body, "Alt"),
        tokens={"--b-background": "#fff"},
        canvas=(1080, 1350),
        images={"social_preview": ("image/png", b"png"), "repo_icon": None},
        box=None,
    )


def test_the_copy_fills_the_slots_and_a_step_gets_its_number() -> None:
    page = _page(_slide(), index=2)

    assert ">Headline<" in page
    assert ">More<" in page
    assert '<span class="fx-badge">3</span>' in page


@pytest.mark.parametrize(
    "template", ["hook", "problem", "step", "proof", "summary", "image", "cta"]
)
def test_every_template_makes_a_page_that_loads_nothing(template: str) -> None:
    page = _page(_slide(template=template))

    assert f"fx-t-{template}" in page
    assert "<script" not in page
    assert "http" not in page.replace("http://www.w3.org", "")


def test_a_picture_is_embedded_in_a_media_box_where_the_plan_says() -> None:
    top = _page(_slide(media="top", image_source="social_preview"))
    bottom = _page(_slide(media="bottom", image_source="social_preview"))

    assert top.index('class="fx-media') < top.index('class="kodalo-headline')
    assert bottom.index('class="fx-media') > bottom.index('class="kodalo-headline')
    assert "data:image/png;base64," in top


def test_an_icon_is_drawn_as_an_svg() -> None:
    page = _page(_slide(icon="git"))

    assert '<svg class="kodalo-icon fx-icon"' in page


def test_a_drawing_becomes_a_one_color_mask_and_the_cta_uses_the_alternate_colors() -> None:
    drawing = fixed_style(
        _slide(image_source="custom_svg", media="top", svg="<svg/>"),
        margins=MARGINS,
        radius=24,
        gap=30,
    )
    cta = fixed_style(_slide(template="cta"), margins=MARGINS, radius=24, gap=30)

    assert "mask:url(" in drawing
    assert "var(--b-background-alt)" in cta
