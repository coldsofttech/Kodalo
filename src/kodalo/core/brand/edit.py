"""Change one value of a brand by its dotted path, for example ``colors.primary.light``."""

from typing import Any

from pydantic import ValidationError

from kodalo.core.brand.errors import BrandInvalidError
from kodalo.core.brand.models import CANVAS_SIZES, BrandData

# Logo files are set by uploading a file, never by typing a name.
_READ_ONLY = {"schema_version", "logo.file", "logo.dark_file"}


def list_paths(data: BrandData) -> list[str]:
    """Return every dotted path that :func:`set_value` can change."""
    paths: list[str] = []

    def walk(node: Any, prefix: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{prefix}.{key}" if prefix else key)
        elif prefix not in _READ_ONLY:
            paths.append(prefix)

    walk(data.model_dump(), "")
    return paths


def _convert(raw: str, current: object, path: str) -> object:
    if isinstance(current, bool):
        lowered = raw.strip().lower()
        if lowered in {"true", "yes", "on", "1"}:
            return True
        if lowered in {"false", "no", "off", "0"}:
            return False
        raise BrandInvalidError(f"{path} must be true or false.")
    if isinstance(current, int):
        try:
            return int(raw)
        except ValueError:
            raise BrandInvalidError(f"{path} must be a whole number.") from None
    return raw


def set_value(data: BrandData, path: str, raw: str) -> BrandData:
    """Return a copy of ``data`` with the value at ``path`` replaced by ``raw``.

    The text is converted to the type of the current value and the whole brand is validated
    again. Choosing a canvas preset also sets its width and height.
    """
    if path in _READ_ONLY:
        raise BrandInvalidError(f"{path} cannot be set this way.")
    tree = data.model_dump()
    node: Any = tree
    *parents, leaf = path.split(".")
    for part in parents:
        node = node.get(part) if isinstance(node, dict) else None
    if not isinstance(node, dict) or leaf not in node or isinstance(node[leaf], dict):
        raise BrandInvalidError(f"Unknown setting: {path}")
    node[leaf] = _convert(raw, node[leaf], path)
    if path == "layout.canvas.preset" and raw in CANVAS_SIZES:
        node["width"], node["height"] = CANVAS_SIZES[raw]
    try:
        return BrandData.model_validate(tree)
    except ValidationError as error:
        problem = error.errors()[0]["msg"]
        raise BrandInvalidError(f"{path}: {problem}") from None
