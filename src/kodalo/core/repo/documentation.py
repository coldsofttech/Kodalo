"""Find the documentation files of a repository by their names. No file is opened."""

import fnmatch
from collections.abc import Iterable

from kodalo.core.repo.models import Documentation, Entry

SECRET_FILES = (".env*", "*.pem", "*.key", "id_rsa*", "*secret*", "*credential*")
_DOCS_DIRS = ("docs", "doc", "documentation")
_KINDS = {
    "changelog": ("changelog*", "changes*", "history*", "news*"),
    "contributing": ("contributing*",),
    "license_file": ("license*", "licence*", "copying*", "unlicense*"),
    "code_of_conduct": ("code_of_conduct*",),
    "security": ("security*",),
}


def is_secret(path: str) -> bool:
    """Whether the file name looks like it holds a secret, so it must not be read."""
    name = path.rsplit("/", 1)[-1].lower()
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in SECRET_FILES)


def find_documentation(entries: Iterable[Entry]) -> Documentation:
    """Pick the README, CHANGELOG, CONTRIBUTING, LICENSE and docs folder from the top level."""
    top = sorted((e for e in entries if "/" not in e.path), key=lambda e: e.path.lower())
    files = [e.path for e in top if e.type == "file"]
    found: dict[str, str] = {}
    for kind, patterns in _KINDS.items():
        for path in files:
            if any(fnmatch.fnmatchcase(path.lower(), p) for p in patterns):
                found[kind] = path
                break
    dirs = {e.path.lower(): e.path for e in top if e.type == "dir"}
    return Documentation(
        readmes=tuple(p for p in files if fnmatch.fnmatchcase(p.lower(), "readme*")),
        docs_dir=next((dirs[name] for name in _DOCS_DIRS if name in dirs), ""),
        **found,
    )
