import io
import socket
import subprocess
import urllib.error
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.tunnel import TunnelError, TunnelManager, manager


class FakeProcess:
    def __init__(self, lines: list[str]) -> None:
        self.stdout = io.StringIO("".join(lines))
        self.stopped = False

    def terminate(self) -> None:
        self.stopped = True

    def wait(self, timeout: float) -> int:
        return 0

    def kill(self) -> None:
        self.stopped = True


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Replace cloudflared: remember how it was started and say it has an address."""
    runs: list[Any] = []

    def popen(command: list[str], **options: Any) -> FakeProcess:
        process = FakeProcess(["INF Starting\n", "INF https://quiet-fox.trycloudflare.com\n"])
        runs.append((command, process))
        return process

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(manager, "_wait_until_fetchable", lambda url: runs.append(url))
    return runs


def test_the_pictures_get_a_public_and_a_local_address_with_the_same_path_and_token(
    tmp_path: Path, started: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    pictures = [tmp_path / "1.jpg", tmp_path / "2.jpg"]
    for picture in pictures:
        picture.write_bytes(b"jpeg")
    tunnel = TunnelManager(tmp_path)
    monkeypatch.setattr(tunnel, "ensure_installed", lambda: Path("cloudflared.exe"))

    with tunnel.serve(pictures) as served:
        command, process = started[0]
        local_port = command[command.index("--url") + 1]
        public, local = served.urls[0], served.local_urls[0]

        assert local_port.startswith("http://127.0.0.1:")
        assert public.startswith(
            "https://quiet-fox.trycloudflare.com/kodalo/instagram/slide-1.jpg?token="
        )
        assert public.split("/kodalo", 1)[1] == local.split("/kodalo", 1)[1]
        assert served.urls[1].split("/kodalo", 1)[1].startswith("/instagram/slide-2.jpg")
        assert started[1] == public

    assert process.stopped


def test_cloudflared_runs_over_https_so_blocked_udp_does_not_stop_it(
    tmp_path: Path, started: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    picture = tmp_path / "1.jpg"
    picture.write_bytes(b"jpeg")
    tunnel = TunnelManager(tmp_path)
    monkeypatch.setattr(tunnel, "ensure_installed", lambda: Path("cloudflared.exe"))

    with tunnel.serve([picture]):
        command = started[0][0]

    assert command[command.index("--protocol") + 1] == "http2"


def test_it_says_whether_cloudflared_is_installed_without_installing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tunnel = TunnelManager(tmp_path)
    monkeypatch.setattr(manager, "find_cloudflared", lambda data_dir: None)
    missing = tunnel.is_installed()
    monkeypatch.setattr(manager, "find_cloudflared", lambda data_dir: Path("cloudflared.exe"))

    assert (missing, tunnel.is_installed()) == (False, True)


@pytest.mark.parametrize(
    ("failure", "said"),
    [
        (urllib.error.URLError(socket.gaierror("no such host")), "look up the address"),
        (urllib.error.URLError("refused"), "no answer"),
        (
            urllib.error.HTTPError("https://t.test", 502, "Bad Gateway", Message(), None),
            "HTTP 502",
        ),
    ],
)
def test_an_address_that_never_answers_says_why(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, said: str
) -> None:
    def refuse(request: Any, timeout: float) -> Any:
        raise failure

    monkeypatch.setattr(manager, "READY_TIMEOUT", 0.05)
    monkeypatch.setattr("kodalo.core.tunnel.manager.time.sleep", lambda seconds: None)
    monkeypatch.setattr("kodalo.core.tunnel.manager.urllib.request.urlopen", refuse)

    with pytest.raises(TunnelError, match=said):
        manager._wait_until_fetchable("https://t.test/slide-1.jpg")


def test_an_address_this_computer_cannot_look_up_is_accepted_when_public_dns_knows_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[str] = []

    class Answer:
        def __enter__(self) -> "Answer":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def read(self, size: int) -> bytes:
            return b'{"Status": 0, "Answer": [{"data": "104.16.0.1"}]}'

    def urlopen(request: Any, timeout: float) -> Any:
        asked.append(request.full_url)
        if request.full_url.startswith(manager.DNS_URL):
            return Answer()
        raise urllib.error.URLError(socket.gaierror("no such host"))

    monkeypatch.setattr("kodalo.core.tunnel.manager.urllib.request.urlopen", urlopen)

    manager._wait_until_fetchable("https://quiet-fox.trycloudflare.com/kodalo/instagram/1.jpg")

    assert asked[1].startswith(manager.DNS_URL)
    assert "name=quiet-fox.trycloudflare.com" in asked[1]


def test_an_address_public_dns_does_not_know_either_still_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def urlopen(request: Any, timeout: float) -> Any:
        raise urllib.error.URLError(socket.gaierror("no such host"))

    monkeypatch.setattr(manager, "READY_TIMEOUT", 0.05)
    monkeypatch.setattr("kodalo.core.tunnel.manager.time.sleep", lambda seconds: None)
    monkeypatch.setattr("kodalo.core.tunnel.manager.urllib.request.urlopen", urlopen)

    with pytest.raises(TunnelError, match="look up the address"):
        manager._wait_until_fetchable("https://quiet-fox.trycloudflare.com/kodalo/instagram/1.jpg")


def test_cloudflared_is_stopped_even_when_the_post_fails(
    tmp_path: Path, started: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    picture = tmp_path / "1.jpg"
    picture.write_bytes(b"jpeg")
    tunnel = TunnelManager(tmp_path)
    monkeypatch.setattr(tunnel, "ensure_installed", lambda: Path("cloudflared.exe"))

    with pytest.raises(ValueError, match="refused"), tunnel.serve([picture]):
        raise ValueError("refused")

    assert started[0][1].stopped


def test_a_missing_installation_stops_before_anything_starts(
    tmp_path: Path, started: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    tunnel = TunnelManager(tmp_path)

    def fail() -> Path:
        raise TunnelError("cloudflared is needed")

    monkeypatch.setattr(tunnel, "ensure_installed", fail)

    with pytest.raises(TunnelError), tunnel.serve([tmp_path / "1.jpg"]):
        pass

    assert started == []
