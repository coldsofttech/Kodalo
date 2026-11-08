"""Smoke test of the built command line: it starts and answers. Needs ``cli.spec`` / ``ui.spec``."""

import json
import subprocess
from pathlib import Path

import pytest

import kodalo.core
from tests.frozen import locate, skip_if_blocked

# cli.spec builds the command line alone; the window (ui.spec) does not ship it.
FOLDERS = ["kodalo"]


def _run(exe: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [str(exe), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
    except OSError as error:
        skip_if_blocked(error, exe)
        raise


@pytest.mark.parametrize("folder", FOLDERS)
def test_reports_its_version(folder: str) -> None:
    result = _run(locate(folder, "kodalo"), "--version")

    assert result.returncode == 0
    assert kodalo.core.__version__ in result.stdout


@pytest.mark.parametrize("folder", FOLDERS)
def test_runs_a_command(folder: str, tmp_path: Path) -> None:
    exe = locate(folder, "kodalo")

    details = _run(exe, "--data-dir", str(tmp_path), "doctor", "--json")

    assert json.loads(details.stdout)["healthy"] is True


@pytest.mark.parametrize("folder", FOLDERS)
def test_reports_errors_with_a_failing_exit_code(folder: str, tmp_path: Path) -> None:
    result = _run(locate(folder, "kodalo"), "--data-dir", str(tmp_path), "brand", "show", "x")

    assert result.returncode == 1
    assert "No brand named" in result.stderr
