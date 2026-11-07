import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from kodalo.cli.cli import app
from kodalo.core.brands.brand import BrandService

runner = CliRunner()


@dataclass
class Studio:
    """A data folder with one repository and one brand to make posts for."""

    data: Path
    repo_id: str

    def invoke(self, *args: str, input: str | None = None) -> tuple[int, str]:
        result = runner.invoke(app, ["--data-dir", str(self.data), "studio", *args], input=input)
        return result.exit_code, result.output

    def post(
        self, step: str, action: str, *extra: str, input: str | None = None
    ) -> tuple[int, str]:
        """Run a copy or design command for the idea of the Acme brand."""
        return self.invoke(
            step, action, self.repo_id, "--brand", "Acme", "--idea", "idea-1", *extra, input=input
        )


@pytest.fixture
def studio(tmp_path: Path) -> Studio:
    data = tmp_path / "data"
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")

    def run(*args: str) -> str:
        result = runner.invoke(app, ["--data-dir", str(data), *args])
        assert result.exit_code == 0, result.output
        return result.output

    run("settings", "github", "set", "local_folder", "--folder", ".")
    added = run(
        "repositories", "add", str(folder), "--owner", "me", "--repo", "proj", "--license", "MIT",
        "--branch", "main", "--json",
    )  # fmt: skip
    run("brand", "create", "Acme")
    return Studio(data, json.loads(added)["id"])


@pytest.fixture
def custom_canvas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every brand look as if its canvas was made for the custom platform."""
    canvas = SimpleNamespace(platform_id="custom", width=100, height=100)
    monkeypatch.setattr(
        BrandService, "find", lambda self, reference: SimpleNamespace(canvas=canvas)
    )


@pytest.fixture
def unsupported_canvas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every brand look as if its canvas was made for a platform with no skill files."""
    canvas = SimpleNamespace(platform_id="tiktok", width=100, height=100)
    monkeypatch.setattr(
        BrandService, "find", lambda self, reference: SimpleNamespace(canvas=canvas)
    )
