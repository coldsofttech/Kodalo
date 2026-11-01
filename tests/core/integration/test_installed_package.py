import subprocess
import sys

import kodalo_package


def test_package_imports_in_fresh_interpreter() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import kodalo_package; print(kodalo_package.__version__)"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == kodalo_package.__version__
