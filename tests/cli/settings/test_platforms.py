import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from kodalo.cli.cli import app

runner = CliRunner()


def invoke(data_dir: Path, *args: str) -> Result:
    return runner.invoke(app, ["--data-dir", str(data_dir), "settings", "platforms", *args])


def test_show_defaults_then_set_and_keep_what_is_left_out(tmp_path: Path) -> None:
    shown = json.loads(invoke(tmp_path, "show", "instagram", "--json").output)
    assert (shown["hashtag_count"], shown["default_hashtags"]) == (5, [])

    first = invoke(tmp_path, "set", "instagram", "--hashtags", "8", "--default-hashtags", "#One")
    second = invoke(tmp_path, "set", "instagram", "--hashtags", "9", "--json")

    assert first.exit_code == 0
    assert json.loads(second.output) == {
        "platform": "instagram",
        "hashtag_count": 9,
        "default_hashtags": ["#one"],
        "use_social_preview": False,
        "use_repo_icon": False,
        "use_icons": False,
        "build_custom_images": False,
        "use_ai_templates": False,
    }


def test_the_visuals_are_switched_on_and_off(tmp_path: Path) -> None:
    on = invoke(tmp_path, "set", "instagram", "--use-social-preview", "--use-icons", "--json")
    off = invoke(tmp_path, "set", "instagram", "--no-social-preview", "--json")

    first, second = json.loads(on.output), json.loads(off.output)
    assert (first["use_social_preview"], first["use_icons"], first["use_repo_icon"]) == (
        True,
        True,
        False,
    )
    assert (second["use_social_preview"], second["use_icons"]) == (False, True)


def test_the_default_hashtags_can_be_removed(tmp_path: Path) -> None:
    invoke(tmp_path, "set", "instagram", "--default-hashtags", "#one")

    invoke(tmp_path, "set", "instagram", "--default-hashtags", "")

    assert (
        json.loads(invoke(tmp_path, "show", "instagram", "--json").output)["default_hashtags"] == []
    )


def test_show_as_a_table(tmp_path: Path) -> None:
    result = invoke(tmp_path, "show", "instagram")

    assert result.exit_code == 0
    assert "Hashtags per post" in result.output
    assert "Default hashtags" in result.output


def test_invalid_values_exit_1(tmp_path: Path) -> None:
    assert invoke(tmp_path, "show", "tiktok").exit_code == 1
    assert invoke(tmp_path, "set", "instagram", "--hashtags", "99").exit_code == 1
    assert (
        invoke(
            tmp_path, "set", "instagram", "--hashtags", "0", "--default-hashtags", "#a"
        ).exit_code
        == 1
    )


def test_instagram_connect_status_and_disconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "kodalo.core.settings.platforms.instagram._fetch_profile",
        lambda token, account_id: {"id": account_id, "username": "sweepito"},
    )

    none = json.loads(invoke(tmp_path, "instagram", "status", "--json").output)
    connected = runner.invoke(
        app,
        ["--data-dir", str(tmp_path), "settings", "platforms", "instagram", "connect", "--json"],
        input="1784140\nIGAA-secret-1234\n",
    )
    status = json.loads(invoke(tmp_path, "instagram", "status", "--json").output)
    disconnected = invoke(tmp_path, "instagram", "disconnect")

    assert none["connected"] is False
    assert connected.exit_code == 0
    assert "IGAA-secret" not in connected.output
    assert (status["username"], status["account_id"], status["token_hint"]) == (
        "sweepito",
        "1784140",
        "1234",
    )
    assert disconnected.exit_code == 0
    assert (
        json.loads(invoke(tmp_path, "instagram", "status", "--json").output)["connected"] is False
    )


def test_instagram_connect_refuses_a_malformed_account_id(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--data-dir", str(tmp_path), "settings", "platforms", "instagram", "connect"],
        input="sweepito\nIGAA-secret-1234\n",
    )

    assert result.exit_code == 1


def test_cloudflared_status_and_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found: list[Path | None] = [None]
    monkeypatch.setattr("kodalo.core.tunnel.manager.find_cloudflared", lambda data_dir: found[0])

    def install(data_dir: Path) -> Path:
        installed = Path("cloudflared.exe")
        found[0] = installed
        return installed

    monkeypatch.setattr("kodalo.core.tunnel.manager.ensure_cloudflared", install)

    before = json.loads(invoke(tmp_path, "instagram", "tunnel", "status", "--json").output)
    installed = invoke(tmp_path, "instagram", "tunnel", "install", "--json")
    after = invoke(tmp_path, "instagram", "tunnel", "status")

    assert before == {"installed": False}
    assert (installed.exit_code, json.loads(installed.output)) == (0, {"installed": True})
    assert "is installed" in after.output


def test_a_failed_cloudflared_install_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from kodalo.core.tunnel import TunnelError

    def fail(data_dir: Path) -> Path:
        raise TunnelError("Could not download cloudflared.")

    monkeypatch.setattr("kodalo.core.tunnel.manager.ensure_cloudflared", fail)

    assert invoke(tmp_path, "instagram", "tunnel", "install").exit_code == 1


def test_instagram_check_when_not_connected_exits_with_an_error(tmp_path: Path) -> None:
    result = invoke(tmp_path, "instagram", "check")

    assert result.exit_code == 1
