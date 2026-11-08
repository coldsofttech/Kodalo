import hashlib
import json
from pathlib import Path

import pytest

from kodalo.core.tunnel import TunnelError, cloudflared, ensure_cloudflared
from kodalo.core.tunnel.manager import find_address

PROGRAM = b"MZ-cloudflared"


@pytest.fixture(autouse=True)
def _nothing_installed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(tmp_path / "empty" / name))
    monkeypatch.setattr("kodalo.core.tunnel.cloudflared.shutil.which", lambda name: None)


def _release(data: bytes = PROGRAM, digest: str | None = None) -> bytes:
    sha = digest or hashlib.sha256(data).hexdigest()
    return json.dumps(
        {
            "assets": [
                {"name": "other.exe", "digest": "sha256:0", "browser_download_url": "x"},
                {
                    "name": cloudflared.ASSET,
                    "digest": f"sha256:{sha}",
                    "browser_download_url": "https://example.test/cloudflared.exe",
                },
            ]
        }
    ).encode()


def _fetcher(release: bytes, data: bytes = PROGRAM):  # type: ignore[no-untyped-def]
    return lambda url: release if url == cloudflared.RELEASE_API else data


def test_an_installed_program_is_used_without_installing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "kodalo.core.tunnel.cloudflared.shutil.which", lambda name: "C:/bin/cloudflared.exe"
    )

    def never(command: list[str]) -> int:
        raise AssertionError("Nothing should be installed.")

    assert ensure_cloudflared(tmp_path, runner=never, platform="win32") == Path(
        "C:/bin/cloudflared.exe"
    )


def test_winget_installs_it_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    program = tmp_path / "winget" / "cloudflared" / "cloudflared.exe"
    program.parent.mkdir(parents=True)
    commands: list[list[str]] = []

    def winget(command: list[str]) -> int:
        commands.append(command)
        program.write_bytes(PROGRAM)
        monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "winget"))
        return 0

    monkeypatch.setattr(
        "kodalo.core.tunnel.cloudflared.shutil.which",
        lambda name: "winget.exe" if name == "winget" else None,
    )

    found = ensure_cloudflared(tmp_path, runner=winget, platform="win32")

    assert found == program
    assert commands[0][:4] == ["winget", "install", "--id", cloudflared.WINGET_ID]
    assert "--silent" in commands[0]


def test_without_winget_the_checked_download_goes_to_the_data_folder(tmp_path: Path) -> None:
    found = ensure_cloudflared(tmp_path, fetcher=_fetcher(_release()), platform="win32")

    assert found == tmp_path / "tools" / "cloudflared.exe"
    assert found.read_bytes() == PROGRAM
    assert not list((tmp_path / "tools").glob("*.part"))


def test_a_failing_winget_falls_back_to_the_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "kodalo.core.tunnel.cloudflared.shutil.which",
        lambda name: "winget.exe" if name == "winget" else None,
    )

    found = ensure_cloudflared(
        tmp_path, runner=lambda command: 1, fetcher=_fetcher(_release()), platform="win32"
    )

    assert found == tmp_path / "tools" / "cloudflared.exe"


def test_a_download_that_does_not_match_its_digest_is_not_kept(tmp_path: Path) -> None:
    with pytest.raises(TunnelError, match="checksum"):
        ensure_cloudflared(tmp_path, fetcher=_fetcher(_release(digest="0" * 64)), platform="win32")

    assert not (tmp_path / "tools").exists()


def test_a_release_without_a_digest_or_the_file_is_refused(tmp_path: Path) -> None:
    for release in (
        b'{"assets": []}',
        b'{"assets": [{"name": "%s"}]}' % cloudflared.ASSET.encode(),
    ):
        with pytest.raises(TunnelError, match="verify"):
            ensure_cloudflared(tmp_path, fetcher=_fetcher(release), platform="win32")


def test_other_systems_are_told_how_to_install_it(tmp_path: Path) -> None:
    with pytest.raises(TunnelError, match=r"developers\.cloudflare\.com"):
        ensure_cloudflared(tmp_path, platform="linux")


def test_the_public_address_is_found_in_cloudflareds_output() -> None:
    line = "INF |  https://random-words-here.trycloudflare.com  |"

    assert find_address(line) == "https://random-words-here.trycloudflare.com"
    assert find_address("INF Requesting new quick Tunnel on trycloudflare.com...") is None
