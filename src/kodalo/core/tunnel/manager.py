"""Give a post's pictures a public address for as long as Instagram needs to fetch them.

``TunnelManager.serve`` starts the local media server on a random port, makes sure cloudflared is
installed, starts a quick tunnel to that port and waits until the pictures can be fetched through
the random ``trycloudflare.com`` address. Everything is stopped when the block ends, so nothing
stays public.
"""

import json
import queue
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from kodalo.core.tunnel.cloudflared import ensure_cloudflared, find_cloudflared
from kodalo.core.tunnel.errors import TunnelError
from kodalo.core.tunnel.media_server import MediaServer

_ADDRESS = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
START_TIMEOUT = 45
READY_TIMEOUT = 60
# Cloudflare's public DNS, asked over HTTPS when this computer cannot look the new address up.
DNS_URL = "https://1.1.1.1/dns-query"


@dataclass(frozen=True)
class ServedImages:
    """The pictures of a post at the public address and at the local one (same path and token)."""

    urls: tuple[str, ...]
    local_urls: tuple[str, ...]


def find_address(line: str) -> str | None:
    """The quick tunnel's public address in a line of cloudflared's output, if it holds one."""
    found = _ADDRESS.search(line)
    return found.group(0) if found else None


class TunnelManager:
    """Installs cloudflared when needed and publishes pictures through a quick tunnel."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def is_installed(self) -> bool:
        """Whether cloudflared is already available, without installing it."""
        return find_cloudflared(self._data_dir) is not None

    def ensure_installed(self) -> Path:
        """The path of cloudflared, installed first if it was missing."""
        return ensure_cloudflared(self._data_dir)

    @contextmanager
    def serve(self, files: Sequence[Path]) -> Iterator[ServedImages]:
        """Publish ``files`` (JPEGs) as ``slide-1.jpg``, ``slide-2.jpg`` and so on. Raises
        ``TunnelError`` when cloudflared is unavailable, does not start or the pictures cannot be
        fetched through it."""
        program = self.ensure_installed()
        names = [f"slide-{number}.jpg" for number in range(1, len(files) + 1)]
        server = MediaServer(dict(zip(names, files, strict=True)))
        server.start()
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(  # noqa: S603
                [
                    str(program),
                    "tunnel",
                    "--no-autoupdate",
                    "--protocol",
                    "http2",
                    "--url",
                    f"http://127.0.0.1:{server.port}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            address = _wait_for_address(process)
            urls = tuple(f"{address}{server.path(name)}" for name in names)
            _wait_until_fetchable(urls[0])
            yield ServedImages(urls, tuple(server.local_url(name) for name in names))
        except OSError as error:
            raise TunnelError("cloudflared could not be started.") from error
        finally:
            if process is not None:
                _stop(process)
            server.stop()


def _wait_for_address(process: subprocess.Popen[str]) -> str:
    found: queue.Queue[str] = queue.Queue()

    def read() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            address = find_address(line)
            if address:
                found.put(address)

    threading.Thread(target=read, daemon=True).start()
    try:
        return found.get(timeout=START_TIMEOUT)
    except queue.Empty as error:
        raise TunnelError("cloudflared did not give a public address in time.") from error


def _wait_until_fetchable(url: str) -> None:
    """Wait until the first picture can be fetched through the public address: the new address
    takes a few seconds to be known everywhere."""
    deadline = time.monotonic() + READY_TIMEOUT
    reason = "no answer"
    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request(url, method="HEAD")  # noqa: S310
            with urllib.request.urlopen(request, timeout=8) as response:  # noqa: S310
                if response.status == 200:
                    return
                reason = f"HTTP {response.status}"
        except urllib.error.HTTPError as error:
            reason = f"HTTP {error.code}"
        except urllib.error.URLError as error:
            if isinstance(error.reason, socket.gaierror):
                # Instagram looks the address up from its own servers, so a resolver here that
                # does not know the new name yet (or blocks it) must not stop the post.
                if _exists_publicly(urllib.parse.urlsplit(url).hostname or ""):
                    return
                reason = "this computer could not look up the address, check your DNS or network"
            else:
                reason = "no answer"
        except (TimeoutError, OSError):
            reason = "no answer"
        time.sleep(2)
    raise TunnelError(f"The public address did not start answering in time ({reason}).")


def _exists_publicly(host: str) -> bool:
    """Whether Cloudflare's public DNS knows ``host``, asked over HTTPS (JSON answer)."""
    query = urllib.parse.urlencode({"name": host, "type": "A"})
    request = urllib.request.Request(  # noqa: S310
        f"{DNS_URL}?{query}", headers={"Accept": "application/dns-json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:  # noqa: S310
            answer = json.loads(response.read(100_000))
    except (OSError, ValueError):
        return False
    return isinstance(answer, dict) and bool(answer.get("Answer"))


def _stop(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
