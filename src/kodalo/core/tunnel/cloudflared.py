"""Find cloudflared on this computer, or install it.

On Windows it is installed with winget; when winget is missing or fails, the program is downloaded
from the official GitHub release into Kodalo's data folder (no administrator rights, no installer)
and its SHA-256 is checked against the digest GitHub lists for the file. Other systems are asked to
install it themselves.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from kodalo.core.tunnel.errors import TunnelError

WINGET_ID = "Cloudflare.cloudflared"
RELEASE_API = "https://api.github.com/repos/cloudflare/cloudflared/releases/latest"
ASSET = "cloudflared-windows-amd64.exe"
MANUAL = (
    "Install cloudflared from "
    "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ "
    "(for example with Homebrew) and try again."
)
_TIMEOUT = 600
_MAX_BYTES = 200 * 1024 * 1024

Runner = Callable[[list[str]], int]
Fetcher = Callable[[str], bytes]


def tools_dir(data_dir: Path) -> Path:
    """Where Kodalo keeps the programs it downloads."""
    return data_dir / "tools"


def find_cloudflared(data_dir: Path) -> Path | None:
    """cloudflared on the path, in Kodalo's own folder, or where winget puts it."""
    found = shutil.which("cloudflared")
    if found:
        return Path(found)
    candidates = [tools_dir(data_dir) / "cloudflared.exe"]
    for variable, parts in (
        ("PROGRAMFILES(X86)", ("cloudflared", "cloudflared.exe")),
        ("PROGRAMFILES", ("cloudflared", "cloudflared.exe")),
        ("LOCALAPPDATA", ("Microsoft", "WinGet", "Links", "cloudflared.exe")),
    ):
        base = os.environ.get(variable)
        if base:
            candidates.append(Path(base).joinpath(*parts))
    return next((path for path in candidates if path.is_file()), None)


def _run(command: list[str]) -> int:
    try:
        return subprocess.run(  # noqa: S603
            command, capture_output=True, timeout=_TIMEOUT, check=False
        ).returncode
    except (OSError, subprocess.TimeoutExpired):
        return -1


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Kodalo"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            data: bytes = response.read(_MAX_BYTES + 1)
    except OSError as error:
        raise TunnelError("Could not download cloudflared.") from error
    if len(data) > _MAX_BYTES:
        raise TunnelError("The cloudflared download is too large.")
    return data


def ensure_cloudflared(
    data_dir: Path,
    *,
    runner: Runner | None = None,
    fetcher: Fetcher | None = None,
    platform: str | None = None,
) -> Path:
    """The path of cloudflared, installing it first when it is missing. Raises ``TunnelError``
    when it cannot be found or installed."""
    found = find_cloudflared(data_dir)
    if found is not None:
        return found
    if (platform or sys.platform) != "win32":
        raise TunnelError(f"cloudflared is needed to post and is not installed. {MANUAL}")
    run = runner or _run
    if shutil.which("winget"):
        code = run(
            [
                "winget",
                "install",
                "--id",
                WINGET_ID,
                "--exact",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
        found = find_cloudflared(data_dir) if code == 0 else None
        if found is not None:
            return found
    return _download(data_dir, fetcher or _fetch)


def _download(data_dir: Path, fetch: Fetcher) -> Path:
    """Download the Windows program into Kodalo's data folder and check it against GitHub's
    digest of the file."""
    try:
        release: Any = json.loads(fetch(RELEASE_API))
        asset = next(a for a in release["assets"] if a["name"] == ASSET)
        digest = str(asset["digest"]).removeprefix("sha256:").lower()
        url = str(asset["browser_download_url"])
    except (ValueError, KeyError, StopIteration, TypeError) as error:
        raise TunnelError("Could not find a cloudflared download to verify.") from error
    data = fetch(url)
    if hashlib.sha256(data).hexdigest() != digest:
        raise TunnelError("The cloudflared download did not match its checksum and was not used.")
    target = tools_dir(data_dir) / "cloudflared.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(target)
    return target
