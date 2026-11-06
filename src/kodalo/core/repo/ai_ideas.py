"""Ask the default AI model once for a content strategy and post ideas for a tool or a feature.

The model is sent only what the README analysis saved: the purpose, and the selected features,
use cases or capabilities with their evidence quotes and the claims that need care. It returns a
strategy, three angles with hooks and five post ideas. A claim is kept only when its quote is one
that was sent, and the claims to avoid are worked out here from the saved analysis, not by the
model. Nothing is saved: the result is shown and reused by the caller.
"""

import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

from kodalo.core.ai import AiConnections
from kodalo.core.repo.ai_parsers import _reply_json, estimate_tokens
from kodalo.core.repo.errors import RepoNotFoundError
from kodalo.core.repo.readme import Feature, ReadmeAnalysis, ReadmeService
from kodalo.core.settings.ai import AiInvalidError

POST_TYPES = ("tool", "feature")
FOCUS_KINDS = ("features", "use_cases", "capabilities")
ANGLE_TYPES = (
    "problem",
    "safety_trust",
    "time_saving",
    "how_it_works",
    "workflow_fit",
    "behind_the_design",
)
HOOK_TYPES = ("question", "bold_statement", "contrast", "curiosity", "number")
FORMATS = ("single_image", "carousel")
CTA_TYPES = ("learn_more", "try_it", "save", "follow", "read_docs")
MAX_ANGLES = 3
MAX_IDEAS = 5
MAX_OUTPUT_TOKENS = 6000
_TOOL_FEATURES = 8


@dataclass(frozen=True)
class Claim:
    text: str
    file: str
    quote: str
    needs_review: bool = False


@dataclass(frozen=True)
class Hook:
    id: str
    text: str
    type: str


@dataclass(frozen=True)
class Angle:
    id: str
    type: str
    name: str
    summary: str
    audience_pain: str
    key_claims: tuple[Claim, ...]
    hooks: tuple[Hook, ...]
    cautions: tuple[str, ...]


@dataclass(frozen=True)
class PostIdea:
    id: str
    angle_id: str
    hook_id: str
    format: str
    working_title: str
    objective: str
    outline: tuple[str, ...]
    visual_concept: str
    asset_needs: tuple[str, ...]
    cta_type: str
    claims_used: tuple[Claim, ...]
    risk_notes: str


@dataclass(frozen=True)
class Strategy:
    objective: str
    audience: str
    pain_points: tuple[str, ...]
    positioning: str
    pillars: tuple[tuple[str, str], ...]
    key_messages: tuple[Claim, ...]


@dataclass(frozen=True)
class AvoidedClaim:
    text: str
    type: str
    reason: str


@dataclass(frozen=True)
class IdeasPlan:
    """What a run would send and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    items: tuple[str, ...]
    input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class Ideas:
    """The strategy, the angles and the post ideas, what was left out and the tokens used."""

    post_type: str
    focus: str
    strategy: Strategy
    angles: tuple[Angle, ...]
    post_ideas: tuple[PostIdea, ...]
    claims_to_avoid: tuple[AvoidedClaim, ...]
    warnings: tuple[str, ...]
    input_tokens: int
    output_tokens: int


def system_prompt() -> str:
    """The instructions sent to every provider: the bundled skill file without its front matter."""
    path = resources.files("kodalo.core.ai") / "prompts" / "marketing"
    text = (path / "marketing-strategist.SKILL.md").read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _text(value: object, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _lines(value: object, limit: int, count: int) -> tuple[str, ...]:
    found = [_text(v, limit) for v in value] if isinstance(value, list) else []
    return tuple(line for line in found if line)[:count]


class IdeasAssistant:
    """Builds the input for one selection and runs the single AI request."""

    def __init__(self, readme: ReadmeService, ai: AiConnections) -> None:
        self._readme = readme
        self._ai = ai

    def _request(
        self, repo_id: str, post_type: str, kind: str, name: str
    ) -> tuple[str, list[str], tuple[AvoidedClaim, ...], tuple[str, ...]]:
        analysis = self._readme.get(repo_id)
        if analysis is None:
            raise RepoNotFoundError("The README analysis has not been read yet.")
        selected, quotes, avoid = _selection(analysis, post_type, kind, name)
        payload = {
            "focus": post_type,
            "product": {"tagline": analysis.tagline, "summary": analysis.summary},
            "selected": selected,
            "claims_to_avoid": [a.text for a in avoid],
        }
        names = tuple(str(item["name"]) for item in selected)
        return json.dumps(payload, ensure_ascii=False, indent=1), quotes, avoid, names

    def plan(self, repo_id: str, post_type: str, kind: str = "", name: str = "") -> IdeasPlan:
        """Work out what would be sent and what asking would cost. Nothing is sent."""
        prompt, _, _, names = self._request(repo_id, post_type, kind, name)
        target = self._ai.default_target()
        return IdeasPlan(
            target.provider,
            target.label,
            target.model,
            names,
            estimate_tokens(system_prompt(), prompt),
            min(MAX_OUTPUT_TOKENS, target.max_tokens or MAX_OUTPUT_TOKENS),
        )

    def generate(self, repo_id: str, post_type: str, kind: str = "", name: str = "") -> Ideas:
        """Ask the model once and return what passes the checks. Raises ``RepoNotFoundError``
        when the analysis or the selection is missing and ``AiInvalidError`` when the selection
        cannot be used or the answer is not in the expected format."""
        prompt, quotes, avoid, _ = self._request(repo_id, post_type, kind, name)
        reply = self._ai.generate(
            system_prompt(),
            prompt,
            MAX_OUTPUT_TOKENS,
            purpose="studio",
            title=f"Post ideas for {name or 'the whole tool'} in {repo_id}",
        )
        data = _reply_json(reply.text)
        if not isinstance(data, dict) or "post_ideas" not in data:
            raise AiInvalidError(
                "The AI did not answer in the expected format, so no ideas were made."
            )
        warnings: list[str] = []
        angles = _angles(data.get("angles"), quotes, warnings)
        ideas = _ideas(data.get("post_ideas"), angles, quotes, warnings)
        return Ideas(
            post_type,
            name,
            _strategy(data.get("strategy"), quotes, warnings),
            angles,
            ideas,
            avoid,
            tuple(warnings),
            reply.input_tokens,
            reply.output_tokens,
        )


def _feature_entry(feature: Feature) -> dict[str, Any]:
    return {
        "kind": "feature",
        "name": feature.name,
        "description": feature.description,
        "importance": feature.importance,
        "maturity": feature.maturity,
        "evidence": [{"file": feature.evidence.file, "quote": feature.evidence.quote}],
        "use_cases": list(feature.use_cases),
        "claims_that_need_care": [c.text for c in feature.claims],
    }


def _selection(
    analysis: ReadmeAnalysis, post_type: str, kind: str, name: str
) -> tuple[list[dict[str, Any]], list[str], tuple[AvoidedClaim, ...]]:
    """What to send, the quotes the answer may cite and the claims that must not be repeated."""
    if post_type not in POST_TYPES:
        raise AiInvalidError("The post type must be tool or feature.")
    features: list[Feature]
    selected: list[dict[str, Any]] = []
    quotes: list[str] = []
    if post_type == "tool":
        rank = {"headline": 0, "supporting": 1, "minor": 2}
        features = sorted(
            (f for f in analysis.features if f.maturity != "planned"),
            key=lambda f: rank.get(f.importance, 1),
        )[:_TOOL_FEATURES]
    else:
        if kind not in FOCUS_KINDS or not name:
            raise AiInvalidError("Choose a feature, use case or capability first.")
        folded = name.casefold()
        features = []
        if kind == "features":
            features = [f for f in analysis.features if f.name.casefold() == folded]
            if features and features[0].maturity == "planned":
                raise AiInvalidError(
                    "The documents call this feature planned, so no post is made about it."
                )
        elif kind == "use_cases":
            case = next((u for u in analysis.use_cases if u.title.casefold() == folded), None)
            if case is not None:
                selected.append(
                    {
                        "kind": "use_case",
                        "name": case.title,
                        "description": case.description,
                        "evidence": [{"file": case.evidence.file, "quote": case.evidence.quote}],
                    }
                )
                quotes.append(case.evidence.quote)
                features = [
                    f
                    for f in analysis.features
                    if folded in (u.casefold() for u in f.use_cases) and f.maturity != "planned"
                ]
        else:
            cap = next((c for c in analysis.capabilities if c.name.casefold() == folded), None)
            if cap is not None:
                selected.append(
                    {
                        "kind": "capability",
                        "name": cap.name,
                        "description": cap.description,
                        "note": cap.note,
                        "evidence": [{"file": cap.evidence.file, "quote": cap.evidence.quote}],
                    }
                )
                quotes.append(cap.evidence.quote)
        if not selected and not features:
            raise RepoNotFoundError("That feature, use case or capability is not in the analysis.")
    avoid: dict[str, AvoidedClaim] = {}
    for feature in features:
        selected.append(_feature_entry(feature))
        quotes.append(feature.evidence.quote)
        for claim in feature.claims:
            avoid.setdefault(
                claim.text.casefold(), AvoidedClaim(claim.text, claim.type, claim.reason)
            )
    # The quotes a claim may cite also include the product's own summary.
    quotes.append(analysis.summary)
    quotes.append(analysis.tagline)
    return selected, quotes, tuple(avoid.values())


def _claim(item: dict[str, Any], quotes: list[str], warnings: list[str]) -> Claim | None:
    """The claim, when its quote really is one that was sent."""
    ref = item.get("evidence_ref")
    ref = ref if isinstance(ref, dict) else {}
    text = _text(item.get("text") or item.get("message"), 200)
    cited = _text(ref.get("quote"), 200)
    if text and cited and any(_squash(cited) in _squash(q) for q in quotes if q):
        return Claim(text, _text(ref.get("file"), 512), cited, item.get("needs_review") is True)
    if text:
        warnings.append(f"A claim was left out because its quote could not be checked: {text[:80]}")
    return None


def _claims(value: object, quotes: list[str], warnings: list[str]) -> tuple[Claim, ...]:
    found = (_claim(item, quotes, warnings) for item in _items(value))
    return tuple(claim for claim in found if claim is not None)


def _strategy(value: object, quotes: list[str], warnings: list[str]) -> Strategy:
    data = value if isinstance(value, dict) else {}
    audience: dict[str, Any] = data["audience"] if isinstance(data.get("audience"), dict) else {}
    pillars = tuple(
        (_text(p.get("name"), 80), _text(p.get("description"), 300))
        for p in _items(data.get("pillars"))[:4]
        if _text(p.get("name"), 80)
    )
    return Strategy(
        _text(data.get("objective"), 300),
        _text(audience.get("primary"), 200),
        _lines(audience.get("pain_points"), 200, 5),
        _text(data.get("positioning"), 300),
        pillars,
        _claims(data.get("key_messages"), quotes, warnings)[:6],
    )


def _angles(value: object, quotes: list[str], warnings: list[str]) -> tuple[Angle, ...]:
    found: list[Angle] = []
    for index, item in enumerate(_items(value)[:MAX_ANGLES], start=1):
        angle_id = _text(item.get("id"), 32) or f"angle-{index}"
        kind = _text(item.get("type"), 32)
        hooks = tuple(
            Hook(
                _text(h.get("id"), 32) or f"hook-{index}-{n}",
                " ".join(_text(h.get("text"), 200).split()[:12]),
                _text(h.get("type"), 32) if _text(h.get("type"), 32) in HOOK_TYPES else "curiosity",
            )
            for n, h in enumerate(_items(item.get("hooks"))[:3], start=1)
            if _text(h.get("text"), 200)
        )
        if not _text(item.get("name"), 80) or not hooks:
            continue
        found.append(
            Angle(
                angle_id,
                kind if kind in ANGLE_TYPES else "problem",
                _text(item.get("name"), 80),
                _text(item.get("summary"), 300),
                _text(item.get("audience_pain"), 300),
                _claims(item.get("key_claims"), quotes, warnings)[:5],
                hooks,
                _lines(item.get("cautions"), 200, 4),
            )
        )
    return tuple(found)


def _ideas(
    value: object, angles: tuple[Angle, ...], quotes: list[str], warnings: list[str]
) -> tuple[PostIdea, ...]:
    known = {a.id: {h.id for h in a.hooks} for a in angles}
    found: list[PostIdea] = []
    for index, item in enumerate(_items(value)[:MAX_IDEAS], start=1):
        angle_id, hook_id = _text(item.get("angle_id"), 32), _text(item.get("hook_id"), 32)
        shape, cta = _text(item.get("format"), 16), _text(item.get("cta_type"), 16)
        title = _text(item.get("working_title"), 120)
        if not title:
            continue
        if angle_id not in known:
            warnings.append(f"{title}: its angle is not in the list, so none is shown for it")
            angle_id = hook_id = ""
        elif hook_id not in known[angle_id]:
            hook_id = ""
        found.append(
            PostIdea(
                _text(item.get("id"), 32) or f"idea-{index}",
                angle_id,
                hook_id,
                shape if shape in FORMATS else "single_image",
                title,
                _text(item.get("objective"), 300),
                _lines(item.get("outline"), 200, 8),
                _text(item.get("visual_concept"), 400),
                _lines(item.get("asset_needs"), 100, 6),
                cta if cta in CTA_TYPES else "learn_more",
                _claims(item.get("claims_used"), quotes, warnings)[:6],
                _text(item.get("risk_notes"), 300),
            )
        )
    return tuple(found)
