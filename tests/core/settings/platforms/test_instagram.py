from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.settings.platforms import (
    InstagramConnection,
    PlatformConnectionError,
    PlatformInvalidError,
)
from kodalo.core.settings.platforms.instagram import SECRET_REF
from kodalo.core.storage import Database, database_path
from tests.conftest import MemorySecrets

ACCOUNT_ID = "1784140"
PROFILE = {"id": ACCOUNT_ID, "username": "sweepito"}


class Fetcher:
    """Stands in for Meta: answers with ``profile`` or fails, and remembers the tokens and IDs."""

    def __init__(self) -> None:
        self.profile: dict[str, Any] = PROFILE
        self.fail = False
        self.tokens: list[str] = []
        self.accounts: list[str] = []

    def __call__(self, token: str, account_id: str) -> dict[str, Any]:
        self.tokens.append(token)
        self.accounts.append(account_id)
        if self.fail:
            raise PlatformConnectionError("Instagram rejected the token.")
        return self.profile


@pytest.fixture
def fetcher() -> Fetcher:
    return Fetcher()


@pytest.fixture
def instagram(tmp_path: Path, fetcher: Fetcher) -> Iterator[InstagramConnection]:
    database = Database.open(database_path(tmp_path))
    yield InstagramConnection(database, MemorySecrets(), fetcher)
    database.close()


def test_starts_disconnected(instagram: InstagramConnection) -> None:
    assert instagram.get() is None


def test_connect_keeps_token_in_keychain_and_only_a_hint_in_settings(
    instagram: InstagramConnection, fetcher: Fetcher
) -> None:
    account = instagram.connect("  IGAA-secret-1234  ", f" {ACCOUNT_ID} ")

    assert fetcher.tokens == ["IGAA-secret-1234"]
    assert fetcher.accounts == [ACCOUNT_ID]
    assert MemorySecrets.values[SECRET_REF] == "IGAA-secret-1234"
    assert (account.username, account.account_id, account.token_hint) == (
        "sweepito",
        "1784140",
        "1234",
    )
    assert instagram.get() == account
    assert "IGAA-secret" not in repr(account)


@pytest.mark.parametrize("token", ["", "   ", "two words", "x" * 1025])
def test_connect_refuses_a_malformed_token_without_calling_instagram(
    instagram: InstagramConnection, fetcher: Fetcher, token: str
) -> None:
    with pytest.raises(PlatformInvalidError):
        instagram.connect(token, ACCOUNT_ID)

    assert fetcher.tokens == []


@pytest.mark.parametrize("account_id", ["", "   ", "sweepito", "12 34", "1" * 41])
def test_connect_refuses_a_malformed_account_id_without_calling_meta(
    instagram: InstagramConnection, fetcher: Fetcher, account_id: str
) -> None:
    with pytest.raises(PlatformInvalidError, match="account ID"):
        instagram.connect("IGAA-token", account_id)

    assert fetcher.tokens == []


def test_a_refused_token_keeps_nothing(instagram: InstagramConnection, fetcher: Fetcher) -> None:
    fetcher.fail = True

    with pytest.raises(PlatformConnectionError):
        instagram.connect("IGAA-bad", ACCOUNT_ID)

    assert instagram.get() is None
    assert SECRET_REF not in MemorySecrets.values


def test_an_answer_without_a_username_is_unreadable(
    instagram: InstagramConnection, fetcher: Fetcher
) -> None:
    fetcher.profile = {"id": ACCOUNT_ID}

    with pytest.raises(PlatformConnectionError):
        instagram.connect("IGAA-token", ACCOUNT_ID)


def test_check_uses_the_saved_token_and_refreshes_the_account(
    instagram: InstagramConnection, fetcher: Fetcher
) -> None:
    first = instagram.connect("IGAA-token-9999", ACCOUNT_ID)
    fetcher.profile = {**PROFILE, "username": "renamed"}

    checked = instagram.check()

    assert fetcher.tokens[-1] == "IGAA-token-9999"
    assert fetcher.accounts[-1] == ACCOUNT_ID
    assert (checked.username, checked.connected_at) == ("renamed", first.connected_at)


def test_check_without_a_connection_fails(instagram: InstagramConnection) -> None:
    with pytest.raises(PlatformConnectionError, match="not connected"):
        instagram.check()


def test_disconnect_removes_token_and_account(instagram: InstagramConnection) -> None:
    instagram.connect("IGAA-token-9999", ACCOUNT_ID)

    instagram.disconnect()
    instagram.disconnect()  # nothing to remove the second time

    assert instagram.get() is None
    assert SECRET_REF not in MemorySecrets.values


class Graph:
    """Stands in for the Instagram API: records the calls and answers like it does."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []
        self.statuses = ["FINISHED"]
        self.created = 0

    def __call__(
        self, method: str, path: str, params: dict[str, str], token: str
    ) -> dict[str, Any]:
        self.calls.append((method, path, params))
        if path.endswith("/media") and method == "POST":
            self.created += 1
            return {"id": f"c{self.created}"}
        if path.endswith("/media_publish"):
            return {"id": "m1"}
        if params.get("fields") == "status_code":
            return {
                "status_code": self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            }
        return {"permalink": "https://www.instagram.com/p/abc/"}


@pytest.fixture
def graph() -> Graph:
    return Graph()


@pytest.fixture
def connected(tmp_path: Path, fetcher: Fetcher, graph: Graph) -> Iterator[InstagramConnection]:
    database = Database.open(database_path(tmp_path))
    instagram = InstagramConnection(database, MemorySecrets(), fetcher, graph)
    instagram.connect("IGAA-token-9999", ACCOUNT_ID)
    yield instagram
    database.close()


def test_one_picture_is_a_single_image_post_with_caption_and_alt_text(
    connected: InstagramConnection, graph: Graph
) -> None:
    posted = connected.publish(["https://x.test/a.jpg"], "Hello #tools", ["A timeline"])

    assert posted.media_id == "m1"
    assert posted.permalink == "https://www.instagram.com/p/abc/"
    create = graph.calls[0]
    assert create[1] == "/1784140/media"
    assert create[2] == {
        "image_url": "https://x.test/a.jpg",
        "caption": "Hello #tools",
        "alt_text": "A timeline",
    }
    assert [c[1] for c in graph.calls if c[0] == "POST"] == [
        "/1784140/media",
        "/1784140/media_publish",
    ]
    assert graph.calls[-2][2] == {"creation_id": "c1"}


def test_several_pictures_are_a_carousel_of_children(
    connected: InstagramConnection, graph: Graph
) -> None:
    connected.publish(
        ["https://x.test/1.jpg", "https://x.test/2.jpg"], "Caption", ["One"], wait=lambda s: None
    )

    posts = [c[2] for c in graph.calls if c[0] == "POST" and c[1].endswith("/media")]
    assert posts[0] == {
        "image_url": "https://x.test/1.jpg",
        "is_carousel_item": "true",
        "alt_text": "One",
    }
    assert posts[1] == {"image_url": "https://x.test/2.jpg", "is_carousel_item": "true"}
    assert posts[2] == {"media_type": "CAROUSEL", "children": "c1,c2", "caption": "Caption"}


def test_it_waits_until_instagram_has_processed_the_pictures(
    connected: InstagramConnection, graph: Graph
) -> None:
    graph.statuses = ["IN_PROGRESS", "IN_PROGRESS", "FINISHED"]
    waits: list[float] = []

    connected.publish(["https://x.test/a.jpg"], "Hi", wait=waits.append)

    assert waits == [2, 2]


def test_a_picture_instagram_cannot_process_fails_the_post(
    connected: InstagramConnection, graph: Graph
) -> None:
    graph.statuses = ["ERROR"]

    with pytest.raises(PlatformConnectionError, match="could not process"):
        connected.publish(["https://x.test/a.jpg"], "Hi", wait=lambda s: None)

    assert not any(c[1].endswith("/media_publish") for c in graph.calls)


@pytest.mark.parametrize(
    ("urls", "caption"),
    [([], "Hi"), (["u"] * 11, "Hi"), (["u"], "x" * 2201), (["u"], "#a " * 31)],
)
def test_a_post_instagram_would_refuse_is_not_sent(
    connected: InstagramConnection, graph: Graph, urls: list[str], caption: str
) -> None:
    with pytest.raises(PlatformInvalidError):
        connected.publish(urls, caption)

    assert graph.calls == []


def test_posting_without_a_connection_fails(instagram: InstagramConnection) -> None:
    with pytest.raises(PlatformConnectionError, match="not connected"):
        instagram.publish(["https://x.test/a.jpg"], "Hi")
