"""The settings a new model starts with.

These are Kodalo's own standards, chosen to be safe for every model of a family; they are not the
limits of any provider. One table, so changing a standard is a one-line edit.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelDefaults:
    """Generation settings: most tokens to write, randomness (0 to 2) and seconds to wait."""

    max_tokens: int
    temperature: float
    timeout_s: int


APP_DEFAULTS = ModelDefaults(max_tokens=4096, temperature=0.7, timeout_s=60)

# The first rule whose word appears in the model name (any case) wins; no match uses APP_DEFAULTS.
FAMILY_DEFAULTS: tuple[tuple[str, ModelDefaults], ...] = (
    ("opus", ModelDefaults(max_tokens=8192, temperature=0.7, timeout_s=120)),
    ("sonnet", ModelDefaults(max_tokens=8192, temperature=0.7, timeout_s=90)),
    ("haiku", ModelDefaults(max_tokens=4096, temperature=0.7, timeout_s=30)),
    ("gemini", ModelDefaults(max_tokens=8192, temperature=0.7, timeout_s=60)),
    ("gpt", ModelDefaults(max_tokens=4096, temperature=0.7, timeout_s=60)),
)


def defaults_for(model_name: str) -> ModelDefaults:
    """Return the starting settings for a model called ``model_name``."""
    lowered = model_name.lower()
    return next(
        (defaults for word, defaults in FAMILY_DEFAULTS if word in lowered),
        APP_DEFAULTS,
    )
