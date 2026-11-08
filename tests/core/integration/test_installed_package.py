import subprocess
import sys

import kodalo.core


def test_package_imports_in_fresh_interpreter() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import kodalo.core; print(kodalo.core.__version__)"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == kodalo.core.__version__
