#!/usr/bin/env python3
"""Write the OpenAPI document to docs/openapi.json.

CI regenerates it and fails if it differs, so the committed contract always matches the code.
Usage: uv run python scripts/export_openapi.py
"""

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer"))
import projectinfo  # noqa: E402

INFO = projectinfo.load()
create_app = importlib.import_module(f"{INFO.api_package}.main").create_app
OUTPUT = ROOT / "docs" / "openapi.json"


def main() -> None:
    spec = create_app().openapi()
    OUTPUT.write_text(
        json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
