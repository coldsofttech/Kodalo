"""A small web server on this computer that hands out the pictures of one post, and nothing else.

It listens on a random port of the loopback address only. A picture is served at
``/kodalo/instagram/<name>.jpg?token=<random token>`` and only with the right token, so the address
that cloudflared makes public is useless to anyone who has not been given the whole link. The
server lives for the length of one post.
"""

import secrets
import threading
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PREFIX = "/kodalo/instagram/"
_HOST = "127.0.0.1"


class MediaServer:
    """Serves the given pictures (name to file) to whoever has the token."""

    def __init__(self, files: Mapping[str, Path]) -> None:
        self.token = secrets.token_urlsafe(24)
        self._files = dict(files)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        """The port the server listens on once started."""
        if self._server is None:
            raise RuntimeError("The media server is not running.")
        return int(self._server.server_address[1])

    def path(self, name: str) -> str:
        """The path and query of one picture, the same on the local and the public address."""
        return f"{PREFIX}{name}?token={self.token}"

    def local_url(self, name: str) -> str:
        return f"http://{_HOST}:{self.port}{self.path(name)}"

    def start(self) -> None:
        files, token = self._files, self.token

        class Handler(BaseHTTPRequestHandler):
            def _send(self, head_only: bool) -> None:
                parts = urlsplit(self.path)
                given = parse_qs(parts.query).get("token", [""])[0]
                name = parts.path.removeprefix(PREFIX)
                file = files.get(name) if parts.path.startswith(PREFIX) else None
                if file is None or not secrets.compare_digest(given, token):
                    self.send_error(404)
                    return
                try:
                    data = file.read_bytes()
                except OSError:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                if not head_only:
                    self.wfile.write(data)

            def do_GET(self) -> None:
                self._send(head_only=False)

            def do_HEAD(self) -> None:
                self._send(head_only=True)

            def log_message(self, format: str, *args: object) -> None:
                """Nothing is logged: the address carries the token."""

        self._server = ThreadingHTTPServer((_HOST, 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
