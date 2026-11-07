"""Making the AI's SVG safe: plain shapes and text only."""

import pytest

from kodalo.core.parsers.svg.sanitize import MAX_SVG_BYTES, sanitize_svg

GOOD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<rect x="1" y="1" width="8" height="8" fill="currentColor"/>'
    '<text x="5" y="5" text-anchor="middle">Hi</text></svg>'
)


def test_plain_shapes_and_text_are_kept() -> None:
    result = sanitize_svg(GOOD)

    assert result is not None
    assert "<rect" in result
    assert ">Hi<" in result
    assert 'viewBox="0 0 10 10"' in result


@pytest.mark.parametrize(
    "markup",
    [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><script>x()</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><image href="http://x/y.png"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><foreignObject/></svg>',
    ],
)
def test_scripts_images_and_other_elements_are_dropped(markup: str) -> None:
    assert sanitize_svg(markup) is None


def test_events_links_styles_and_remote_references_are_removed() -> None:
    result = sanitize_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect width="5" height="5" onclick="x()" style="fill:url(http://x)" fill="url(http://x/a)"/>'
        '<circle r="2" fill="url(#g)" xlink:href="http://x" stroke="red"/>'
        "</svg>".replace("xlink:href", "href")
    )

    assert result is not None
    for forbidden in ("onclick", "style", "http://x", "href"):
        assert forbidden not in result.replace("http://www.w3.org/2000/svg", "")
    assert 'fill="url(#g)"' in result
    assert 'stroke="red"' in result


def test_entities_doctype_size_and_shape_are_refused() -> None:
    assert sanitize_svg('<!DOCTYPE svg [<!ENTITY a "b">]>' + GOOD) is None
    assert sanitize_svg(GOOD.replace("<svg", "<!-- x --><svg", 1) + "<") is None
    assert sanitize_svg("not xml") is None
    assert sanitize_svg("") is None
    assert sanitize_svg('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>') is None
    assert sanitize_svg(GOOD.replace("</svg>", "<g/>" * MAX_SVG_BYTES + "</svg>")) is None
    assert sanitize_svg("<html/>") is None
    assert sanitize_svg('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>') is None
