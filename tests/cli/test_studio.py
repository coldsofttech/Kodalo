import json
from pathlib import Path

from typer.testing import CliRunner

from kodalo.cli.cli import app

runner = CliRunner()


def invoke(data_dir: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), *args])
    return result.exit_code, result.output


def test_source_github_and_invalid(tmp_path: Path) -> None:
    code, out = invoke(tmp_path, "studio", "source", "owner/repo", "--json")
    assert code == 0
    assert json.loads(out)["value"] == "https://github.com/owner/repo"
    assert invoke(tmp_path, "studio", "source", "nonsense")[0] == 1


def test_source_follows_local_folder_mode(tmp_path: Path) -> None:
    invoke(tmp_path, "settings", "github", "set", "local_folder", "--folder", str(tmp_path))
    assert invoke(tmp_path, "studio", "source", str(tmp_path))[0] == 0
    assert invoke(tmp_path, "studio", "source", "owner/repo")[0] == 1
