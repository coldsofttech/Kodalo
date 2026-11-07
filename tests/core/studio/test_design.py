"""Planning the layout of a written post with the AI, keeping it, and checking every choice."""

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from kodalo.core.ai import AiTarget, Generation
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.platforms import Platforms
from kodalo.core.storage import Database, database_path
from kodalo.core.storage.models import Repository
from kodalo.core.studio import design as ds
from kodalo.core.studio.copy import AltOpening, Caption, Choice, PostCopy, Slide
from kodalo.core.studio.design import DesignAssistant

CHOICE = Choice("instagram", "r1", "feature", "features", "Hooks", "idea-1", "")
CANVAS = (1080, 1350)
SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
    '<circle cx="5" cy="5" r="4" stroke="currentColor" fill="none"/></svg>'
)


def _post(format_: str = "carousel") -> PostCopy:
    slides = tuple(
        Slide(role, f"Headline {n}", "Body", "A picture of a commit timeline", "Alt")
        for n, role in enumerate(("hook", "step", "cta"), 1)
    )
    return PostCopy(
        "instagram",
        "idea-1",
        "hook-1",
        "Hook",
        format_,
        slides[:1] if format_ == "single_image" else slides,
        Caption("Opening", ("Line",), "Cta"),
        AltOpening("Other", ""),
        ("#a",),
        (),
        (),
        1,
        1,
    )


def _slide(**changes: Any) -> dict[str, Any]:
    plan = {
        "template": "step",
        "align": "left",
        "media": "none",
        "accent": "primary",
        "icon": "",
        "image": {"source": "none", "fit": "cover", "svg": ""},
    }
    image = {**plan["image"], **changes.pop("image", {})}  # type: ignore[dict-item]
    return {**plan, **changes, "image": image}


class FakeAi:
    def __init__(self, reply: object) -> None:
        self.reply = reply
        self.images: tuple[tuple[str, bytes], ...] = ()
        self.prompt = ""

    def default_target(self, task: str | None = None) -> AiTarget:
        return AiTarget("claude_api", "Claude API", "haiku", None, None, None)

    def generate(self, system: str, prompt: str, max_tokens: int, **kwargs: Any) -> Generation:
        self.prompt = prompt
        self.images = kwargs.get("images", ())
        return Generation(json.dumps(self.reply), 10, 20)


class FakeRepos:
    """Just what the designer asks of the repository service."""

    def __init__(self, preview: Path | None = None, icon: bool = False) -> None:
        self.preview = preview
        self.icon = icon
        self.box: tuple[float, float, float, float] | None = None
        self.checked = False

    def get(self, repo_id: str) -> Any:
        return SimpleNamespace(
            name="Sweepito",
            has_icon=self.icon,
            icon_box=self.box,
            icon_box_checked=self.checked,
        )

    def social_preview(self, repo_id: str) -> tuple[Path, str] | None:
        return (self.preview, "image/png") if self.preview else None

    def save_icon_box(self, repo_id: str, box: tuple[float, float, float, float] | None) -> None:
        self.box, self.checked = box, True


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path / "data"))
    with db.session() as session:
        session.add(Repository(id="r1", url="https://github.com/o/r", owner="o", name="r"))
    yield db
    db.close()


def _assistant(
    database: Database, ai: FakeAi, repos: FakeRepos, post: PostCopy | None = None
) -> DesignAssistant:
    found = post if post is not None else _post()
    copy = SimpleNamespace(saved=lambda choice: found)
    return DesignAssistant(
        copy,  # type: ignore[arg-type]
        repos,  # type: ignore[arg-type]
        Platforms(database),
        ai,  # type: ignore[arg-type]
        database,
    )


def _reply(*slides: dict[str, Any], box: object = None) -> dict[str, Any]:
    return {"slides": list(slides), "logo_box": box}


def test_the_plan_is_checked_kept_and_given_back(database: Database) -> None:
    Platforms(database).save("instagram", 5, [], use_icons=True)
    ai = FakeAi(
        _reply(
            _slide(template="hook", align="center", icon="bi-git", accent="secondary"),
            _slide(template="proof", icon="terminal"),
            _slide(template="nonsense", align="right", icon="not-an-icon"),
        )
    )
    assistant = _assistant(database, ai, FakeRepos())

    design = assistant.generate(CHOICE, CANVAS)

    assert [s.template for s in design.slides] == ["hook", "proof", "cta"]
    assert (design.slides[0].align, design.slides[0].icon) == ("center", "git")
    assert design.slides[1].icon == "terminal"
    assert (design.slides[2].align, design.slides[2].icon) == ("center", "")
    assert any("not-an-icon" in w for w in design.warnings)
    assert (design.input_tokens, design.output_tokens) == (10, 20)
    assert assistant.saved(CHOICE) == design
    assert '"icons": true' in ai.prompt


def test_icons_are_dropped_when_the_setting_is_off(database: Database) -> None:
    ai = FakeAi(_reply(_slide(icon="git"), _slide(), _slide()))

    design = _assistant(database, ai, FakeRepos()).generate(CHOICE, CANVAS)

    assert [s.icon for s in design.slides] == ["", "", ""]


def test_only_allowed_and_available_images_are_used(database: Database, tmp_path: Path) -> None:
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\n")
    Platforms(database).save("instagram", 5, [], use_social_preview=True)
    ai = FakeAi(
        _reply(
            _slide(image={"source": "social_preview", "fit": "contain"}),
            _slide(image={"source": "repo_icon"}),
            _slide(image={"source": "custom_svg", "svg": SVG}),
        )
    )

    design = _assistant(database, ai, FakeRepos(preview)).generate(CHOICE, CANVAS)

    assert (design.slides[0].image_source, design.slides[0].media) == ("social_preview", "top")
    assert design.slides[0].image_fit == "contain"
    assert design.slides[1].image_source == "none"
    assert design.slides[2].image_source == "none"
    assert len(design.warnings) == 2
    assert ai.images == ()


def test_a_custom_drawing_is_cleaned_served_and_refused_when_unsafe(database: Database) -> None:
    Platforms(database).save("instagram", 5, [], build_custom_images=True)
    unsafe = SVG.replace("<circle", "<script>x()</script><circle")
    ai = FakeAi(
        _reply(
            _slide(image={"source": "custom_svg", "svg": SVG}),
            _slide(
                image={"source": "custom_svg", "svg": unsafe.replace("<script>x()</script>", "")}
            ),
            _slide(image={"source": "custom_svg", "svg": "<svg onload='x()'/>"}),
        )
    )
    assistant = _assistant(database, ai, FakeRepos())

    design = assistant.generate(CHOICE, CANVAS)

    assert design.slides[0].image_source == "custom_svg"
    assert "<circle" in (assistant.svg(CHOICE, 0) or "")
    assert design.slides[2].image_source == "none"
    assert assistant.svg(CHOICE, 2) is None
    assert assistant.svg(CHOICE, 9) is None


def test_the_logo_is_looked_for_in_the_social_preview_once(
    database: Database, tmp_path: Path
) -> None:
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\n")
    Platforms(database).save("instagram", 5, [], use_repo_icon=True)
    repos = FakeRepos(preview)
    box = {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.3}
    ai = FakeAi(_reply(_slide(image={"source": "repo_icon"}), _slide(), _slide(), box=box))
    assistant = _assistant(database, ai, repos)

    plan = assistant.plan(CHOICE, CANVAS)
    design = assistant.generate(CHOICE, CANVAS)

    assert plan.sees_social_preview
    assert plan.input_tokens >= ds.IMAGE_TOKENS
    assert len(ai.images) == 1
    assert design.logo_box == (0.1, 0.2, 0.3, 0.3)
    assert design.slides[0].image_source == "repo_icon"
    again = FakeAi(_reply(_slide(), _slide(), _slide()))
    assert not _assistant(database, again, repos).plan(CHOICE, CANVAS).sees_social_preview
    _assistant(database, again, repos).generate(CHOICE, CANVAS)
    assert again.images == ()


def test_no_logo_in_the_preview_means_no_repo_icon(database: Database, tmp_path: Path) -> None:
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\n")
    Platforms(database).save("instagram", 5, [], use_repo_icon=True)
    ai = FakeAi(_reply(_slide(image={"source": "repo_icon"}), _slide(), _slide(), box=None))

    design = _assistant(database, ai, FakeRepos(preview)).generate(CHOICE, CANVAS)

    assert design.logo_box is None
    assert design.slides[0].image_source == "none"


def test_a_single_image_always_uses_the_image_template(database: Database) -> None:
    ai = FakeAi(_reply(_slide(template="hook")))

    design = _assistant(database, ai, FakeRepos(), _post("single_image")).generate(CHOICE, CANVAS)

    assert [s.template for s in design.slides] == ["image"]


def test_missing_slides_get_the_plain_design_and_a_warning(database: Database) -> None:
    design = _assistant(database, FakeAi(_reply(_slide())), FakeRepos()).generate(CHOICE, CANVAS)

    assert len(design.slides) == 3
    assert sum("no design for slide" in w for w in design.warnings) == 2


def test_bad_answers_and_missing_copy_are_refused(database: Database) -> None:
    with pytest.raises(AiInvalidError):
        _assistant(database, FakeAi({"nothing": 1}), FakeRepos()).generate(CHOICE, CANVAS)
    missing = DesignAssistant(
        SimpleNamespace(saved=lambda choice: None),  # type: ignore[arg-type]
        FakeRepos(),  # type: ignore[arg-type]
        Platforms(database),
        FakeAi({}),  # type: ignore[arg-type]
        database,
    )
    with pytest.raises(RepoNotFoundError):
        missing.plan(CHOICE, CANVAS)


def test_the_plan_says_what_is_sent(database: Database) -> None:
    plan = _assistant(database, FakeAi({}), FakeRepos()).plan(CHOICE, CANVAS)

    assert plan.items == ("Headline 1",)
    assert plan.input_tokens > 0
    assert not plan.sees_social_preview


STYLE = ".s { display: flex; flex-direction: column; height: 100%; } .icon { font-size: 128px; }"


def _layout(extra: str = "", **changes: str) -> dict[str, str]:
    markup = f'<div class="s">{extra}<h1 data-slot="headline"></h1><p data-slot="body"></p></div>'
    return {"layout": markup, "accent": "", **changes}


def _answer(*slides: dict[str, str], **changes: Any) -> dict[str, Any]:
    answer: dict[str, Any] = {
        "style": STYLE,
        "slides": list(slides),
        "repo_name": "first_last",
        "progress": "dots",
        "logo_box": None,
    }
    return {**answer, **changes}


def _brand(database: Database, tmp_path: Path) -> Any:
    from kodalo.core.brands.brand import BrandService

    return BrandService(database, tmp_path).create("Main")


def _ai_mode(database: Database, **settings: bool) -> None:
    Platforms(database).save("instagram", 5, [], use_ai_templates=True, **settings)


def test_ai_layouts_are_checked_and_a_failing_one_keeps_the_fixed_template(
    database: Database,
) -> None:
    _ai_mode(database, use_icons=True)
    diagram = (
        '<div class="timeline"><span class="a"></span><span class="b"></span>'
        '<span class="c"></span><span class="d"></span></div>'
    )
    ai = FakeAi(
        _answer(
            _layout('<i data-icon="git" class="icon"></i><script>x()</script>', accent="Headline"),
            _layout(diagram),
            _layout('<i class="bi bi-terminal icon"></i>', accent="not in the headline"),
            repo_name="last",
            progress="bar",
        )
    )
    assistant = _assistant(database, ai, FakeRepos())

    design = assistant.generate(CHOICE, CANVAS)

    first, second, third = design.slides
    assert '<i data-icon="git" class="icon"></i>' in first.html
    assert "script" not in first.html
    assert first.emphasis == "Headline"
    assert (second.html, second.template) == ("", "step")
    assert 'data-icon="terminal"' in third.html  # the Bootstrap class form is understood
    assert third.emphasis == ""
    assert design.style == STYLE
    assert (design.repo_name, design.progress) == ("last", "bar")
    assert [("diagram" in w) for w in design.warnings] == [True]
    assert assistant.saved(CHOICE) == design
    assert '"icons": true' in ai.prompt


def test_a_stylesheet_that_is_not_safe_means_the_fixed_templates(database: Database) -> None:
    _ai_mode(database)
    bad = _answer(_layout(), _layout(), _layout(), style=".s { color: red !important; }")

    design = _assistant(database, FakeAi(bad), FakeRepos()).generate(CHOICE, CANVAS)

    assert all(not slide.html for slide in design.slides)
    assert design.style == ""
    assert any("stylesheet" in w for w in design.warnings)


def test_the_ai_never_supplies_the_words(database: Database, tmp_path: Path) -> None:
    _ai_mode(database)
    brand = _brand(database, tmp_path)
    written = '<div class="s">Invented words<h1 data-slot="headline">Invented headline</h1></div>'
    ai = FakeAi(_answer({"layout": written}, _layout(), _layout()))
    assistant = _assistant(database, ai, FakeRepos())
    assistant.generate(CHOICE, CANVAS)

    page = assistant.slide_page(CHOICE, 0, brand, "light", ds.PageAssets())

    assert page is not None
    body = page.split("</style>")[1]
    assert "Invented" not in body
    assert "Headline 1" in body
    assert "Body" in body  # the slide has a body, so a body slot was added


def test_the_ai_html_prompt_is_used_and_costs_more_output(database: Database) -> None:
    _ai_mode(database)
    assistant = _assistant(database, FakeAi({}), FakeRepos())

    plan = assistant.plan(CHOICE, CANVAS)

    assert plan.writes_html
    assert plan.max_output_tokens == ds.MAX_HTML_OUTPUT_TOKENS
    assert "stylesheet shared by every slide" in ds.system_prompt("instagram", html=True)
    assert "stylesheet shared by every slide" not in ds.system_prompt("instagram")
    assert "stylesheet shared by every slide" in ds.system_prompt("custom", html=True)
    assert "stylesheet shared by every slide" not in ds.system_prompt("custom")


def test_the_page_has_the_brand_colors_for_the_mode_and_the_slide_number(
    database: Database, tmp_path: Path
) -> None:
    _ai_mode(database)
    brand = _brand(database, tmp_path)
    assistant = _assistant(database, FakeAi(_answer(_layout(), _layout(), _layout())), FakeRepos())
    assistant.generate(CHOICE, CANVAS)

    light = assistant.slide_page(CHOICE, 1, brand, "light", ds.PageAssets())
    dark = assistant.slide_page(CHOICE, 1, brand, "dark", ds.PageAssets())

    assert light is not None
    assert dark is not None
    assert f"--b-background:{brand.data.colors.background.light};" in light
    assert f"--b-background:{brand.data.colors.background.dark};" in dark
    assert f"width:{brand.canvas.width}px" in light
    assert "2/3" in light
    assert "kodalo-progress" in light
    assert assistant.slide_page(CHOICE, 7, brand, "light", ds.PageAssets()) is None


def test_the_brand_logo_is_embedded_and_the_repo_name_stands_in_when_there_is_none(
    database: Database, tmp_path: Path
) -> None:
    _ai_mode(database)
    plain = _brand(database, tmp_path)
    with_logo = plain.model_copy(deep=True)
    with_logo.data.logo.file = "logo.png"
    assistant = _assistant(
        database, FakeAi(_answer(_layout(), _layout(), _layout(), repo_name="none")), FakeRepos()
    )
    assistant.generate(CHOICE, CANVAS)
    logo = ("image/png", b"\x89PNG\r\n")

    shown = assistant.slide_page(CHOICE, 0, with_logo, "light", ds.PageAssets(logo_light=logo))
    named = assistant.slide_page(CHOICE, 0, plain, "light", ds.PageAssets())
    unreadable = assistant.slide_page(CHOICE, 0, with_logo, "light", ds.PageAssets())

    assert shown is not None
    assert named is not None
    assert unreadable is not None
    assert 'class="kodalo-logo" src="data:image/png;base64,' in shown
    assert "kodalo-wordmark" not in shown.split("</style>")[1]
    assert '<span class="kodalo-wordmark">Sweepito</span>' in named
    assert "kodalo-wordmark" in unreadable  # a logo that cannot be read is replaced by the name


def test_the_ai_decides_on_which_slides_the_repo_name_shows(
    database: Database, tmp_path: Path
) -> None:
    _ai_mode(database)
    brand = _brand(database, tmp_path)
    brand = brand.model_copy(deep=True)
    brand.data.logo.show_on = "none"  # no wordmark, so the footer is the only place for the name
    where: dict[str, list[int]] = {}
    for place in ("all", "first_last", "first", "last", "none"):
        answer = _answer(_layout(), _layout(), _layout(), repo_name=place)
        assistant = _assistant(database, FakeAi(answer), FakeRepos())
        assistant.generate(CHOICE, CANVAS)
        where[place] = [
            i
            for i in range(3)
            if "<span>Sweepito"
            in (assistant.slide_page(CHOICE, i, brand, "light", ds.PageAssets()) or "")
        ]

    assert where == {"all": [0, 1, 2], "first_last": [0, 2], "first": [0], "last": [2], "none": []}


def test_an_allowed_picture_the_ai_left_out_is_added_and_embedded(
    database: Database, tmp_path: Path
) -> None:
    _ai_mode(database, use_social_preview=True)
    brand = _brand(database, tmp_path)
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\n")
    ai = FakeAi(_answer(_layout(), _layout(), _layout()))
    assistant = _assistant(database, ai, FakeRepos(preview))

    design = assistant.generate(CHOICE, CANVAS)
    assets = ds.PageAssets(social_preview=ds.load_image(preview, "image/png"))
    page = assistant.slide_page(CHOICE, 0, brand, "light", assets)

    assert 'data-asset="social_preview"' in design.slides[0].html
    assert any("added the social preview to slide 1" in w for w in design.warnings)
    assert page is not None
    assert 'class="kodalo-auto" src="data:image/png;base64,' in page
    assert "img-src" not in page  # a page needs no policy of its own: nothing is loaded


def test_a_picture_the_ai_used_is_not_added_twice(database: Database, tmp_path: Path) -> None:
    _ai_mode(database, use_social_preview=True)
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\n")
    ai = FakeAi(
        _answer(_layout('<img data-asset="social_preview" class="photo">'), _layout(), _layout())
    )

    design = _assistant(database, ai, FakeRepos(preview)).generate(CHOICE, CANVAS)

    assert design.slides[0].html.count("data-asset") == 1
    assert not any("none of the pictures" in w for w in design.warnings)


def test_icons_that_are_on_but_unused_are_flagged(database: Database) -> None:
    _ai_mode(database, use_icons=True)
    ai = FakeAi(_answer(_layout(), _layout(), _layout()))

    design = _assistant(database, ai, FakeRepos()).generate(CHOICE, CANVAS)

    assert any("no icons" in w for w in design.warnings)


def test_a_design_saved_before_shared_styles_shows_the_fixed_templates() -> None:
    old = json.dumps(
        {
            "platform": "instagram",
            "idea_id": "idea-1",
            "hook_id": "hook-1",
            "slides": [
                {
                    "template": "hook",
                    "align": "left",
                    "media": "none",
                    "accent": "primary",
                    "icon": "",
                    "image_source": "none",
                    "image_fit": "cover",
                    "svg": "",
                    "html": "<div>old</div>",
                    "css": "div{}",
                }
            ],
            "logo_box": None,
            "warnings": [],
            "input_tokens": 1,
            "output_tokens": 1,
        }
    )

    design = ds._design_from_json(old)

    assert design.slides[0].html == ""
    assert design.style == ""


def test_a_fixed_template_slide_is_a_page_with_the_copy(database: Database, tmp_path: Path) -> None:
    brand = _brand(database, tmp_path)
    assistant = _assistant(
        database,
        FakeAi(_reply(_slide(template="hook", align="center"), _slide(), _slide())),
        FakeRepos(),
    )
    assistant.generate(CHOICE, CANVAS)

    page = assistant.slide_page(CHOICE, 0, brand, "light", ds.PageAssets())

    assert page is not None
    assert "fx-slide fx-center fx-primary fx-t-hook" in page
    assert 'class="kodalo-headline fx-title"' in page
    assert "<script" not in page
    assert assistant.slide_page(CHOICE, 7, brand, "light", ds.PageAssets()) is None


def test_a_warning_says_when_none_of_the_allowed_pictures_was_used(
    database: Database, tmp_path: Path
) -> None:
    preview = tmp_path / "preview.png"
    preview.write_bytes(b"\x89PNG\r\n\x1a\n")
    Platforms(database).save("instagram", 5, [], use_social_preview=True)
    ai = FakeAi(_reply(_slide(), _slide(), _slide()))

    design = _assistant(database, ai, FakeRepos(preview)).generate(CHOICE, CANVAS)

    assert any("none of the pictures" in w for w in design.warnings)
