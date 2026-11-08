import json
import subprocess
import sys
from pathlib import Path

import kodalo.core


def _run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_module_entrypoint() -> None:
    result = _run(sys.executable, "-m", "kodalo.cli", "--version")

    assert result.returncode == 0
    assert kodalo.core.__version__ in result.stdout


def test_console_script(tmp_path: Path) -> None:
    script = Path(sys.executable).parent / ("kodalo.exe" if sys.platform == "win32" else "kodalo")

    result = _run(str(script), "--data-dir", str(tmp_path), "doctor", "--json")

    assert result.returncode == 0
    assert json.loads(result.stdout)["healthy"] is True


def test_errors_go_to_stderr(tmp_path: Path) -> None:
    result = _run(
        sys.executable, "-m", "kodalo.cli", "--data-dir", str(tmp_path), "brand", "show", "x"
    )

    assert result.returncode == 1
    assert "No brand named" in result.stderr
    assert result.stdout == ""
