import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.tunnel import MediaServer


@pytest.fixture
def server(tmp_path: Path) -> Iterator[MediaServer]:
    first = tmp_path / "a.jpg"
    first.write_bytes(b"jpeg-bytes")
    secret = tmp_path / "secret.txt"
    secret.write_text("not a picture", encoding="utf-8")
    running = MediaServer({"slide-1.jpg": first})
    running.start()
    yield running
    running.stop()


def _get(url: str, method: str = "GET") -> tuple[int, bytes, str]:
    request = urllib.request.Request(url, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as r:  # noqa: S310
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        return error.code, b"", ""


def test_a_picture_is_served_at_the_kodalo_instagram_path_with_the_token(
    server: MediaServer,
) -> None:
    url = server.local_url("slide-1.jpg")

    assert "/kodalo/instagram/slide-1.jpg?token=" in url
    assert _get(url) == (200, b"jpeg-bytes", "image/jpeg")
    assert _get(url, "HEAD")[0] == 200


def test_the_port_is_random_and_only_the_loopback_address_listens(server: MediaServer) -> None:
    assert server.port > 1024
    assert server.local_url("slide-1.jpg").startswith("http://127.0.0.1:")


@pytest.mark.parametrize(
    "tail",
    [
        "/kodalo/instagram/slide-1.jpg",
        "/kodalo/instagram/slide-1.jpg?token=wrong",
        "/kodalo/instagram/other.jpg?token={token}",
        "/kodalo/instagram/../secret.txt?token={token}",
        "/slide-1.jpg?token={token}",
        "/",
    ],
)
def test_anything_but_the_right_name_with_the_right_token_is_not_found(
    server: MediaServer, tail: str
) -> None:
    url = f"http://127.0.0.1:{server.port}{tail.format(token=server.token)}"

    assert _get(url)[0] == 404


def test_each_server_has_its_own_token(tmp_path: Path) -> None:
    assert MediaServer({}).token != MediaServer({}).token
