"""Ask the default AI model for a new palette that differs from the existing ones."""

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

from pydantic import ValidationError

from kodalo.core.ai import AiConnections
from kodalo.core.brands.brand.models import BrandColors
from kodalo.core.brands.palette.models import Palette
from kodalo.core.brands.palette.service import PaletteService
from kodalo.core.repositories.ai.parsers import estimate_tokens
from kodalo.core.settings.ai import AiInvalidError

MAX_OUTPUT_TOKENS = 1024
MAX_NAME = 64


@dataclass(frozen=True)
class PalettePlan:
    """What a suggestion would send and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    palettes: int
    input_tokens: int
    max_output_tokens: int


def system_prompt() -> str:
    """The instructions sent to every provider: the bundled skill file without its front matter."""
    prompt = resources.files("kodalo.core.ai") / "prompts" / "palette" / "palette-suggest.SKILL.md"
    text = prompt.read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def build_prompt(palettes: list[Palette]) -> str:
    """The existing palettes as JSON, so the model can avoid repeating them."""
    existing = [{"name": p.name, "colors": p.colors.model_dump()} for p in palettes]
    return "Existing palettes:\n" + json.dumps(existing, indent=1)


def _reply_json(text: str) -> Any:
    """The JSON object in a model's answer, which may be wrapped in a code fence or in prose."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except ValueError:
        return None


def _free_name(wanted: str, taken: set[str]) -> str:
    name = wanted[:MAX_NAME]
    number = 2
    while name.lower() in taken:
        suffix = f" {number}"
        name = f"{wanted[: MAX_NAME - len(suffix)]}{suffix}"
        number += 1
    return name


class PaletteSuggester:
    """Suggests palettes with the default AI connection. Nothing is saved."""

    def __init__(self, palettes: PaletteService, ai: AiConnections) -> None:
        self._palettes = palettes
        self._ai = ai

    def plan(self) -> PalettePlan:
        """Work out what a suggestion would send and cost. Nothing is sent."""
        existing = self._palettes.list_palettes()
        target = self._ai.default_target("palette")
        return PalettePlan(
            provider=target.provider,
            label=target.label,
            model=target.model,
            palettes=len(existing),
            input_tokens=estimate_tokens(system_prompt(), build_prompt(existing)),
            max_output_tokens=min(MAX_OUTPUT_TOKENS, target.max_tokens or MAX_OUTPUT_TOKENS),
        )

    def suggest(self) -> tuple[str, BrandColors]:
        """Return a suggested name and colors. Raises ``AiInvalidError`` when the model's answer
        cannot be used, and ``AiConnectionError`` when it cannot be reached."""
        existing = self._palettes.list_palettes()
        reply = self._ai.generate(
            system_prompt(),
            build_prompt(existing),
            MAX_OUTPUT_TOKENS,
            purpose="palette",
            title="Suggest a palette",
            task="palette",
        )
        data = _reply_json(reply.text)
        name = data.get("name") if isinstance(data, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise AiInvalidError("The AI did not answer in the expected format. Try again.")
        try:
            colors = BrandColors.model_validate(data.get("colors"))
        except ValidationError as error:
            raise AiInvalidError(
                "The AI suggested colors that are not valid. Try again."
            ) from error
        return _free_name(name.strip(), {p.name.lower() for p in existing}), colors
