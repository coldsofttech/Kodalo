"""The social preview image of a GitHub repository, if its owner uploaded one.

The REST API does not expose it, but GraphQL does: ``usesCustomOpenGraphImage`` says whether there
is a custom image, and ``openGraphImageUrl`` is where it is. Only the ``gh`` CLI is used, since it
is signed in. Every failure means "no image": the preview is a nicety, never a reason to fail.
"""

import json
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

_TIMEOUT = 20
MAX_BYTES = 5 * 1024 * 1024
_HOST_SUFFIX = ".githubusercontent.com"
_QUERY = (
    "query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) "
    "{ openGraphImageUrl usesCustomOpenGraphImage } }"
)

# Reads the image of ``owner/repo``: the bytes, or None when there is none.
PreviewFetch = Callable[[str, str], bytes | None]


def image_type(data: bytes) -> str | None:
    """Return ``png`` or ``jpg`` from the first bytes, or None for anything else."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    return None


def _custom_image_url(owner: str, repo: str) -> str | None:
    gh = shutil.which("gh")
    if gh is None:
        return None
    result = subprocess.run(  # noqa: S603
        [
            gh,
            "api",
            "graphql",
            "-f",
            f"query={_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={repo}",
        ],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
        check=False,
    )
    if result.returncode != 0:
        return None
    node = ((json.loads(result.stdout).get("data") or {}).get("repository")) or {}
    url = node.get("openGraphImageUrl")
    if not node.get("usesCustomOpenGraphImage") or not isinstance(url, str):
        return None
    parts = urllib.parse.urlparse(url)
    if parts.scheme != "https" or not (parts.hostname or "").endswith(_HOST_SUFFIX):
        return None
    return url


def gh_social_preview(owner: str, repo: str) -> bytes | None:
    """Download the custom social preview of ``owner/repo``; None when it has none."""
    try:
        url = _custom_image_url(owner, repo)
        if url is None:
            return None
        request = urllib.request.Request(url, headers={"User-Agent": "kodalo"})  # noqa: S310
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
            data: bytes = response.read(MAX_BYTES + 1)
    except (OSError, subprocess.SubprocessError, urllib.error.URLError, ValueError, TimeoutError):
        return None
    return data if len(data) <= MAX_BYTES and image_type(data) else None
