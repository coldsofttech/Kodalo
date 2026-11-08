#!/usr/bin/env python3
"""Generate the release notes and the Scoop manifest for a release.

Used by .github/workflows/release.yml; everything comes from pyproject.toml, uv.lock and the
CHANGELOG, so renaming the project needs no edit here.

    name                                              the command and package name (kodalo)
    notes    --version 0.1.0                          the CHANGELOG section, for the release notes
    scoop    --version 0.1.0 --zip-sha256 HEX --repo owner/name --out bucket/kodalo.json

winget needs no generated file: the workflow submits the setup.exe through winget-releaser.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer"))
import projectinfo  # noqa: E402

INFO = projectinfo.load()
PROJECT: dict[str, Any] = INFO.project
CLI_SCRIPT = INFO.cli_script  # the command and package name, a [tool.installer] key


# ---- release notes -------------------------------------------------------------------------------
def release_notes(version: str) -> str:
    """The CHANGELOG section of ``version``, or a pointer to the file if there is none."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    pattern = rf"^## \[v?{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
    match = re.search(pattern, changelog, re.MULTILINE | re.DOTALL)
    body = match.group(1).strip() if match else ""
    return body or "See [CHANGELOG.md](CHANGELOG.md) for the changes in this release."


# ---- Scoop ---------------------------------------------------------------------------------------
def zip_name(version: str) -> str:
    return f"{CLI_SCRIPT}-{version}-windows-x64.zip"


def scoop_manifest(version: str, zip_sha256: str, repo: str) -> str:
    base = f"https://github.com/{repo}/releases/download"
    manifest = {
        "version": version,
        "description": PROJECT.get("description", CLI_SCRIPT),
        "homepage": (PROJECT.get("urls") or {}).get("Homepage", f"https://github.com/{repo}"),
        "license": PROJECT.get("license", ""),
        "architecture": {
            "64bit": {"url": f"{base}/v{version}/{zip_name(version)}", "hash": zip_sha256}
        },
        "bin": f"{CLI_SCRIPT}.exe",
        "checkver": "github",
        "autoupdate": {
            "architecture": {"64bit": {"url": f"{base}/v$version/{zip_name('$version')}"}}
        },
    }
    return json.dumps(manifest, indent=4) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("name")
    for name in ("notes", "scoop"):
        command = sub.add_parser(name)
        command.add_argument("--version", required=True)
        command.add_argument("--out", type=Path, help="write here instead of stdout")
    sub.choices["scoop"].add_argument("--zip-sha256", required=True)
    sub.choices["scoop"].add_argument("--repo", required=True, help="owner/name of the repository")
    args = parser.parse_args()

    if args.command == "name":
        print(CLI_SCRIPT)
        return
    if args.command == "notes":
        text = release_notes(args.version) + "\n"
    else:
        text = scoop_manifest(args.version, args.zip_sha256, args.repo)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
