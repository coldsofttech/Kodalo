from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.settings.platforms import (
    DEFAULT_HASHTAG_COUNT,
    MAX_HASHTAGS,
    PlatformInvalidError,
    Platforms,
    clean_hashtags,
)
from kodalo.core.storage import Database, database_path


@pytest.fixture
def platforms(tmp_path: Path) -> Iterator[Platforms]:
    database = Database.open(database_path(tmp_path))
    yield Platforms(database)
    database.close()


def test_instagram_starts_with_five_hashtags_and_no_default_ones(platforms: Platforms) -> None:
    settings = platforms.get("instagram")

    assert (settings.hashtag_count, settings.default_hashtags) == (DEFAULT_HASHTAG_COUNT, ())


def test_the_settings_are_saved_and_cleaned(platforms: Platforms) -> None:
    saved = platforms.save("instagram", 12, ["#Sweepito", "dev tools", "sweepito", "#"])

    assert saved.default_hashtags == ("#sweepito", "#devtools")
    assert platforms.get("instagram") == saved
    assert platforms.save("instagram", 3, "#a, #b").default_hashtags == ("#a", "#b")


def test_a_bad_platform_count_or_default_list_is_refused(platforms: Platforms) -> None:
    with pytest.raises(PlatformInvalidError):
        platforms.get("tiktok")
    with pytest.raises(PlatformInvalidError):
        platforms.save("instagram", MAX_HASHTAGS + 1, [])
    with pytest.raises(PlatformInvalidError):
        platforms.save("instagram", -1, [])
    with pytest.raises(PlatformInvalidError, match="default hashtags"):
        platforms.save("instagram", 1, ["#a", "#b"])


def test_the_visuals_are_off_until_chosen_and_are_kept(platforms: Platforms) -> None:
    first = platforms.get("instagram")
    assert not any((first.use_social_preview, first.use_repo_icon, first.use_icons))
    assert not first.build_custom_images
    assert not first.use_ai_templates

    platforms.save("instagram", 5, [], use_social_preview=True, build_custom_images=True)
    kept = platforms.get("instagram")

    assert (kept.use_social_preview, kept.use_repo_icon, kept.use_icons) == (True, False, False)
    assert kept.build_custom_images


def test_zero_hashtags_is_allowed(platforms: Platforms) -> None:
    assert platforms.save("instagram", 0, []).hashtag_count == 0


def test_clean_hashtags_ignores_what_is_not_text() -> None:
    assert clean_hashtags(None) == ()
    assert clean_hashtags([1, "#Ok", ["x"]]) == ("#ok",)
    assert clean_hashtags(["#a", "#b", "#c"], 2) == ("#a", "#b")
