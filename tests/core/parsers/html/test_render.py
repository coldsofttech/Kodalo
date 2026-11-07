"""AI-written slide layouts: what is kept, what is refused, and the page that is built."""

from typing import Any

import pytest

from kodalo.core.parsers.html.render import (
    Chrome,
    SlideText,
    brand_tokens,
    build_page,
    clean_css,
    clean_layout,
    icons,
    type_scale,
    with_picture,
    with_slots,
)

LAYOUT = (
    '<div class="slide"><i data-icon="git" class="icon"></i>'
    '<h1 data-slot="headline" class="title"></h1><p data-slot="body"></p></div>'
)
TEXT = SlideText(
    "What if cleanup ran after each commit?", "After the commit step.", "A timeline", "after each"
)
STYLE = ".slide { display: flex; } .title { color: var(--b-primary); }"
HEADLINE = '<h1 data-slot="headline"></h1>'


def _clean(markup: str = LAYOUT, **kwargs: Any) -> Any:
    options: dict[str, Any] = {
        "assets": {"social_preview"},
        "allow_icons": True,
        "allow_svg": False,
    }
    options.update(kwargs)
    return clean_layout(
        markup,
        options["assets"],
        allow_icons=options["allow_icons"],
        allow_svg=options["allow_svg"],
    )


def _page(layout: str = LAYOUT, **kwargs: Any) -> str:
    options: dict[str, Any] = {
        "tokens": {},
        "canvas": (1080, 1350),
        "images": {},
        "box": None,
        "chrome": None,
    }
    options.update(kwargs)
    return build_page(layout, STYLE, options.pop("text", TEXT), **options)


def _body(page: str) -> str:
    return page.split("</style>")[1]


def test_slots_icons_and_classes_are_kept_and_counted() -> None:
    layout = _clean()

    assert layout.html == LAYOUT
    assert (layout.headline, layout.body) == (True, True)
    assert (layout.icons, layout.pictures, layout.decorations) == (1, 0, 0)


def test_no_text_of_its_own_survives() -> None:
    layout = _clean(
        '<div>Written words<h1 data-slot="headline">Written headline<b>x</b></h1>'
        "<span>more words</span><p>loose paragraph</p></div>"
    )

    assert layout.html == '<div><h1 data-slot="headline"></h1><span></span></div>'


@pytest.mark.parametrize(
    "markup",
    [
        f"<div><script>alert(1)</script>{HEADLINE}</div>",
        f'<div onclick="x()" style="color:red">{HEADLINE}</div>',
        f'<div><iframe src="http://x">hidden</iframe>{HEADLINE}</div>',
        f'<div><a href="http://x">link</a>{HEADLINE}</div>',
        f'<div><form action="/x"><input name="q">Search</form>{HEADLINE}</div>',
        f'<div><link rel="stylesheet" href="http://x"><meta http-equiv="refresh">{HEADLINE}</div>',
    ],
)
def test_scripts_links_forms_frames_and_attributes_are_removed(markup: str) -> None:
    html = _clean(markup).html

    for forbidden in ("script", "onclick", "style=", "iframe", "href", "<form", "<input", "<link"):
        assert forbidden not in html
    assert "<meta" not in html
    assert 'data-slot="headline"' in html


def test_pictures_are_placeholders_for_allowed_assets_only() -> None:
    kept = _clean('<div><img data-asset="social_preview" src="http://x/a.png" class="photo"></div>')
    dropped = _clean('<div><img data-asset="repo_icon"></div>')
    other = _clean('<div><img src="http://x/a.png"></div>')

    assert '<img data-asset="social_preview" class="photo">' in kept.html
    assert "http://x" not in kept.html
    assert (kept.pictures, dropped.pictures, other.pictures) == (1, 0, 0)
    assert "<img" not in dropped.html + other.html


def test_icons_are_names_that_exist_and_only_when_allowed() -> None:
    markup = (
        '<div><i data-icon="git" class="icon"></i><i data-icon="not-an-icon"></i>'
        '<i class="bi bi-terminal"></i><i class="bi bi-nope">words</i></div>'
    )

    on = _clean(markup)
    off = _clean(markup, allow_icons=False)

    assert on.html.count("data-icon") == 2  # git, and terminal written the Bootstrap class way
    assert 'data-icon="terminal"' in on.html
    assert "not-an-icon" not in on.html
    assert "bi-" not in on.html
    assert "words" not in on.html
    assert on.icons == 2
    assert "data-icon" not in off.html
    assert {"git", "terminal"} <= set(icons())


def test_a_diagram_made_of_empty_boxes_is_refused_unless_custom_images_are_allowed() -> None:
    timeline = (
        '<div class="timeline"><span class="line"></span><span class="node"></span>'
        '<span class="node"></span><span class="node"></span></div>'
    )

    with pytest.raises(ValueError, match="diagram"):
        _clean(f"<div>{timeline}{HEADLINE}</div>")
    assert _clean(f"<div>{timeline}{HEADLINE}</div>", allow_svg=True)
    assert _clean(f'<div><span class="rule"></span><span class="rule"></span>{HEADLINE}</div>')


def test_inline_drawings_are_cleaned_and_only_when_allowed() -> None:
    drawing = (
        '<svg viewBox="0 0 10 10" onload="x()"><script>x()</script>'
        '<circle cx="5" cy="5" r="4" fill="var(--b-primary)"/><text>Words</text>'
        '<image href="http://x/a.png"/></svg>'
    )

    kept = _clean(f"<div>{drawing}</div>", allow_svg=True).html
    off = _clean(f"<div>{drawing}{HEADLINE}</div>").html

    assert "<circle" in kept
    assert "viewBox" in kept
    for forbidden in ("onload", "script", "image", "http://x", "Words", "<text"):
        assert forbidden not in kept
    assert "<svg" not in off


def test_large_or_empty_layouts_are_refused() -> None:
    with pytest.raises(ValueError, match="large"):
        _clean("<div>" + "x" * 20000 + "</div>")
    with pytest.raises(ValueError, match="nothing"):
        _clean("<script>x()</script>")


def test_missing_slots_are_added_so_the_copy_always_shows() -> None:
    none = _clean('<div class="a"><span></span></div>')
    headline_only = _clean(f"<div>{HEADLINE}</div>")

    assert with_slots(none, body=True) == (
        '<div class="a"><span></span><h1 data-slot="headline"></h1><p data-slot="body"></p></div>'
    )
    assert with_slots(headline_only, body=False) == headline_only.html
    assert with_slots(headline_only, body=True).endswith('<p data-slot="body"></p></div>')
    assert with_picture('<div class="a"></div>', "social_preview").startswith(
        '<div class="a"><img data-asset="social_preview" class="kodalo-auto">'
    )


@pytest.mark.parametrize(
    "css",
    [
        "@import 'x.css'; h1 { color: red }",
        "h1 { background: url(http://x/a.png) }",
        "@font-face { font-family: x; src: local(x) }",
        "h1 { width: expression(alert(1)) }",
        "h1 { color: \\72ed }",
        "h1 { behavior: x }",
        "h1 { color: red !important }",
        "</style><script>x()</script>",
        "",
    ],
)
def test_a_stylesheet_that_could_load_or_run_anything_is_refused(css: str) -> None:
    assert clean_css(css) is None


def test_comments_are_dropped_and_size_is_limited() -> None:
    assert clean_css("/* hi */ h1 { color: red }") == "h1 { color: red }"
    assert clean_css("h1{color:red}" * 2000) is None


def test_the_type_scale_is_fixed_by_length_and_canvas() -> None:
    short = type_scale("Short", "Body", 1080)
    long = type_scale("x" * 100, "y" * 120, 1080)
    wide = type_scale("Short", "Body", 2160)

    assert "font-size:96px!important" in short
    assert "font-size:38px!important" in short
    assert "font-size:52px!important" in long
    assert "font-size:34px!important" in long
    assert "font-size:192px!important" in wide


def test_the_page_fills_the_slots_with_the_copy_and_nothing_else() -> None:
    page = _page(text=SlideText("A <b>bold</b> idea", "Body & more", "alt"))
    body = _body(page)

    assert '<h1 class="kodalo-headline title">A &lt;b&gt;bold&lt;/b&gt; idea</h1>' in body
    assert '<p class="kodalo-body">Body &amp; more</p>' in body
    assert "<script" not in page
    assert STYLE in page
    assert "width:1080px;height:1350px" in page


def test_a_phrase_of_the_headline_can_be_set_apart() -> None:
    body = _body(_page())

    assert 'ran <span class="kodalo-accent">after each</span> commit?' in body
    assert 'class="kodalo-accent"' not in _body(
        _page(text=SlideText("A headline", "", "alt", "no"))
    )


def test_the_page_has_the_brand_embedded_pictures_and_drawn_icons() -> None:
    tokens = brand_tokens(
        {"background": "#101010", "text_alt": "#eeeeee"}, {"heading": 'My "Font"', "mono": "Code"}
    )
    layout = _clean(
        '<div><i data-icon="git" class="big"></i><img data-asset="social_preview" class="photo">'
        f'<img data-asset="repo_icon" class="mark">{HEADLINE}</div>',
        assets={"social_preview", "repo_icon"},
    ).html

    page = _page(
        layout,
        tokens=tokens,
        images={"social_preview": ("image/png", b"\x89PNG\r\n"), "repo_icon": None},
        box=(0.1, 0.2, 0.3, 0.4),
    )

    assert tokens["--b-background"] == "#101010"
    assert tokens["--f-heading"] == '"My Font", sans-serif'
    assert tokens["--f-mono"] == '"Code", monospace'
    body = _body(page)
    assert '<svg class="kodalo-icon big"' in body
    assert 'class="photo" src="data:image/png;base64,' in body
    assert 'class="kodalo-crop mark"' in body  # no icon file: the logo is cut from the preview
    assert "http" not in body


def test_a_picture_without_a_source_is_left_out() -> None:
    page = _page(f'<div><img data-asset="repo_icon">{HEADLINE}</div>')

    assert "<img" not in _body(page)


def _chrome(**changes: Any) -> Chrome:
    fields: dict[str, Any] = {
        "logo": ("image/png", b"\x89PNG\r\n"),
        "wordmark": "",
        "logo_position": "top_left",
        "logo_percent": 14,
        "logo_padding": 48,
        "footer_text": "Footer <b>",
        "repo_name": "",
        "slide_number": "2/5",
        "margin_side": 80,
        "margin_bottom": 96,
        "progress": "none",
        "index": 1,
        "total": 5,
    }
    fields.update(changes)
    return Chrome(**fields)


def test_the_logo_footer_and_slide_number_are_drawn_by_the_app() -> None:
    page = _page(chrome=_chrome(logo_position="bottom_right"))

    body = _body(page)
    assert 'class="kodalo-logo" src="data:image/png;base64,' in body
    assert "bottom:48px;right:48px" in page
    assert "width:151px" in page  # 14 % of the canvas width
    assert "<span>Footer &lt;b&gt;</span><span>2/5</span>" in body
    assert "justify-content:flex-start" in page  # a logo bottom right keeps the footer to the left
    assert "kodalo-logo" not in _body(_page())


def test_the_repo_name_stands_in_for_a_missing_logo_and_shows_in_the_footer() -> None:
    wordmark = _body(_page(chrome=_chrome(logo=None, wordmark="Sweepito")))
    footer = _body(_page(chrome=_chrome(logo=None, repo_name="Sweepito")))

    assert '<span class="kodalo-wordmark">Sweepito</span>' in wordmark
    assert "kodalo-logo" not in wordmark
    assert "<span>Sweepito · Footer &lt;b&gt;</span>" in footer
    assert "kodalo-wordmark" not in footer


def _css(page: str) -> str:
    return page.split("<style>")[1].split("</style>")[0]


def test_progress_marks_are_drawn_the_same_on_every_slide() -> None:
    first = _page(chrome=_chrome(progress="dots", index=0, slide_number="1/5"))
    third = _page(chrome=_chrome(progress="dots", index=2, slide_number="3/5"))
    bar = _page(chrome=_chrome(progress="bar", index=4))
    none = _page(chrome=_chrome(progress="none"))

    assert '<span class="on"></span><span class=""></span>' in first
    assert '<span class="done"></span><span class="done"></span><span class="on"></span>' in third
    assert _css(first).split(".kodalo-progress{")[1] == _css(third).split(".kodalo-progress{")[1]
    assert "width:22px!important;height:22px!important" in _css(first)
    assert "kodalo-bar span{flex:1" in _css(bar)
    assert "kodalo-progress" not in _body(none)
    assert "kodalo-progress" not in _body(_page(chrome=_chrome(progress="dots", total=1)))
