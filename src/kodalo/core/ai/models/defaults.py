"""Shipped generation defaults (max tokens, temperature, timeout) for well-known models.

Keyed by provider id. A provider such as Claude Code that names models by alias (``opus``) points
each alias at the entry of the full model it stands for.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


@dataclass(frozen=True)
class ModelDefaults:
    """Generation defaults for one model. ``temperature_range`` is ``(minimum, maximum)``."""

    max_tokens: int
    temperature: float
    temperature_range: tuple[float, float]
    timeout_s: int


@dataclass(frozen=True)
class _Table:
    models: dict[str, dict[str, ModelDefaults]]
    aliases: dict[str, dict[str, tuple[str, str]]]


@lru_cache(maxsize=1)
def _load() -> _Table:
    raw = json.loads(
        resources.files("kodalo.core.ai.models").joinpath("defaults.json").read_text("utf-8")
    )
    models = {
        provider: {
            name: ModelDefaults(
                max_tokens=int(entry["max_tokens"]),
                temperature=float(entry["temperature"]),
                temperature_range=(
                    float(entry["temperature_range"][0]),
                    float(entry["temperature_range"][1]),
                ),
                timeout_s=int(entry["timeout_s"]),
            )
            for name, entry in entries.items()
        }
        for provider, entries in raw["models"].items()
    }
    aliases = {
        provider: {alias: (target[0], target[1]) for alias, target in entries.items()}
        for provider, entries in raw["aliases"].items()
    }
    return _Table(models, aliases)


def model_defaults(provider: str, model: str) -> ModelDefaults | None:
    """Return the shipped defaults for ``model`` under ``provider``, or ``None`` if unknown."""
    table = _load()
    found = table.models.get(provider, {}).get(model)
    if found is not None:
        return found
    target = table.aliases.get(provider, {}).get(model)
    if target is None:
        return None
    return table.models.get(target[0], {}).get(target[1])
