"""Ask the default AI model once for a content strategy and post ideas for a tool or a feature.

The model is sent only what the README analysis saved: the purpose, and the selected features,
use cases or capabilities with their evidence quotes and the claims that need care. It returns a
strategy, three angles with hooks and the chosen number of post ideas. A claim is kept only
when its quote is one that was sent, and the claims to avoid are worked out here from the saved
analysis, not by the model. A new run adds its ideas to the saved ones.
"""

import json
import re
from dataclasses import asdict, dataclass, replace
from importlib import resources
from typing import Any

from sqlalchemy import select

from kodalo.core.ai import AiConnections
from kodalo.core.repositories.ai.parsers import _reply_json, estimate_tokens
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.repositories.readme import Feature, ReadmeAnalysis, ReadmeService
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.storage import Database
from kodalo.core.storage.models import StudioIdeas

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
BASE_OUTPUT_TOKENS = 2000
TOKENS_PER_IDEA = 800
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
    posted: bool = False


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


def output_tokens(count: int) -> int:
    """The most tokens the answer may use for ``count`` post ideas."""
    return BASE_OUTPUT_TOKENS + TOKENS_PER_IDEA * count


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

    def __init__(self, readme: ReadmeService, ai: AiConnections, database: Database) -> None:
        self._readme = readme
        self._ai = ai
        self._database = database

    def saved(self, repo_id: str, post_type: str, kind: str = "", name: str = "") -> Ideas | None:
        """The ideas kept for this repository and focus, or ``None`` when none were made yet."""
        with self._database.session() as session:
            row = session.scalars(
                select(StudioIdeas).where(
                    StudioIdeas.repository_id == repo_id,
                    StudioIdeas.focus_key == _focus_key(post_type, kind, name),
                )
            ).first()
            return _ideas_from_json(row.payload) if row is not None else None

    def mark_posted(
        self, repo_id: str, post_type: str, kind: str, name: str, idea_id: str, posted: bool
    ) -> PostIdea:
        """Flag the idea ``idea_id`` as posted, or clear the flag. Raises ``RepoNotFoundError``
        when the ideas or the idea are not saved."""
        saved = self.saved(repo_id, post_type, kind, name)
        found = next((i for i in saved.post_ideas if i.id == idea_id), None) if saved else None
        if saved is None or found is None:
            raise RepoNotFoundError("That post idea is not saved.")
        changed = replace(found, posted=posted)
        updated = tuple(changed if i.id == idea_id else i for i in saved.post_ideas)
        self._save(repo_id, post_type, kind, name, replace(saved, post_ideas=updated))
        return changed

    def _saved_ideas(
        self, repo_id: str, post_type: str, kind: str, name: str
    ) -> tuple[PostIdea, ...]:
        found = self.saved(repo_id, post_type, kind, name)
        return found.post_ideas if found is not None else ()

    def _save(self, repo_id: str, post_type: str, kind: str, name: str, ideas: Ideas) -> None:
        payload = json.dumps(asdict(ideas), ensure_ascii=False)
        key = _focus_key(post_type, kind, name)
        with self._database.session() as session:
            row = session.scalars(
                select(StudioIdeas).where(
                    StudioIdeas.repository_id == repo_id, StudioIdeas.focus_key == key
                )
            ).first()
            if row is None:
                session.add(StudioIdeas(repository_id=repo_id, focus_key=key, payload=payload))
            else:
                row.payload = payload

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
            "post_idea_count": self._ai.idea_count(),
            "already_made": [
                i.working_title for i in self._saved_ideas(repo_id, post_type, kind, name)
            ],
            "selected": selected,
            "claims_to_avoid": [a.text for a in avoid],
        }
        names = tuple(str(item["name"]) for item in selected)
        return json.dumps(payload, ensure_ascii=False, indent=1), quotes, avoid, names

    def _limit(self) -> int:
        return output_tokens(self._ai.idea_count())

    def plan(self, repo_id: str, post_type: str, kind: str = "", name: str = "") -> IdeasPlan:
        """Work out what would be sent and what asking would cost. Nothing is sent."""
        prompt, _, _, names = self._request(repo_id, post_type, kind, name)
        target = self._ai.default_target("studio_ideas")
        return IdeasPlan(
            target.provider,
            target.label,
            target.model,
            names,
            estimate_tokens(system_prompt(), prompt),
            min(self._limit(), target.max_tokens or self._limit()),
        )

    def generate(self, repo_id: str, post_type: str, kind: str = "", name: str = "") -> Ideas:
        """Ask the model once and return what passes the checks. Raises ``RepoNotFoundError``
        when the analysis or the selection is missing and ``AiInvalidError`` when the selection
        cannot be used or the answer is not in the expected format."""
        prompt, quotes, avoid, _ = self._request(repo_id, post_type, kind, name)
        reply = self._ai.generate(
            system_prompt(),
            prompt,
            self._limit(),
            purpose="studio",
            title=f"Post ideas for {name or 'the whole tool'} in {repo_id}",
            task="studio_ideas",
        )
        data = _reply_json(reply.text)
        if not isinstance(data, dict) or "post_ideas" not in data:
            raise AiInvalidError(
                "The AI did not answer in the expected format, so no ideas were made."
            )
        warnings: list[str] = []
        angles = _angles(data.get("angles"), quotes, warnings)
        ideas = _ideas(data.get("post_ideas"), angles, quotes, warnings, self._ai.idea_count())
        made = Ideas(
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
        previous = self.saved(repo_id, post_type, kind, name)
        if previous is not None:
            made = _merge(previous, made)
        self._save(repo_id, post_type, kind, name, made)
        return made


def _free_id(taken: set[str], wanted: str, prefix: str) -> str:
    """``wanted`` when no one has it, else the next unused ``prefix-N``."""
    if wanted and wanted not in taken:
        return wanted
    number = len(taken) + 1
    while f"{prefix}-{number}" in taken:
        number += 1
    return f"{prefix}-{number}"


def _merge(old: Ideas, new: Ideas) -> Ideas:
    """Add what a new run made to what was saved. Saved angles, hooks and ideas stay as they are
    (copy and designs refer to them); a new angle or hook the saved ones already have is not added
    again, and neither is an idea with the same title. The saved strategy is kept."""
    angles = list(old.angles)
    angle_ids = {a.id for a in angles}
    hook_ids = {h.id for a in angles for h in a.hooks}
    angle_map: dict[str, str] = {}
    hook_map: dict[str, str] = {}
    for angle in new.angles:
        same = next((a for a in angles if _squash(a.name) == _squash(angle.name)), None)
        if same is None:
            fresh = _free_id(angle_ids, angle.id, "angle")
            angle_ids.add(fresh)
            hooks = []
            for hook in angle.hooks:
                hook_id = _free_id(hook_ids, hook.id, "hook")
                hook_ids.add(hook_id)
                hook_map[hook.id] = hook_id
                hooks.append(replace(hook, id=hook_id))
            angle_map[angle.id] = fresh
            angles.append(replace(angle, id=fresh, hooks=tuple(hooks)))
            continue
        angle_map[angle.id] = same.id
        known = {_squash(h.text): h for h in same.hooks}
        extra = list(same.hooks)
        for hook in angle.hooks:
            match = known.get(_squash(hook.text))
            if match is not None:
                hook_map[hook.id] = match.id
                continue
            hook_id = _free_id(hook_ids, hook.id, "hook")
            hook_ids.add(hook_id)
            hook_map[hook.id] = hook_id
            extra.append(replace(hook, id=hook_id))
        angles[angles.index(same)] = replace(same, hooks=tuple(extra))
    ideas = list(old.post_ideas)
    idea_ids = {i.id for i in ideas}
    titles = {_squash(i.working_title) for i in ideas}
    skipped = 0
    for idea in new.post_ideas:
        if _squash(idea.working_title) in titles:
            skipped += 1
            continue
        idea_id = _free_id(idea_ids, idea.id, "idea")
        idea_ids.add(idea_id)
        titles.add(_squash(idea.working_title))
        ideas.append(
            replace(
                idea,
                id=idea_id,
                angle_id=angle_map.get(idea.angle_id, ""),
                hook_id=hook_map.get(idea.hook_id, ""),
            )
        )
    warnings = list(new.warnings)
    if skipped:
        warnings.append(f"{skipped} idea(s) already made were left out")
    return replace(
        new,
        strategy=old.strategy,
        angles=tuple(angles),
        post_ideas=tuple(ideas),
        warnings=tuple(warnings),
    )


def _focus_key(post_type: str, kind: str, name: str) -> str:
    return f"{post_type}|{kind}|{name}"[:600]


def _claims_from(items: list[dict[str, Any]]) -> tuple[Claim, ...]:
    return tuple(Claim(**item) for item in items)


def _ideas_from_json(payload: str) -> Ideas:
    """Rebuild what ``asdict`` wrote when the ideas were saved."""
    data = json.loads(payload)
    strategy = data["strategy"]
    return Ideas(
        data["post_type"],
        data["focus"],
        Strategy(
            strategy["objective"],
            strategy["audience"],
            tuple(strategy["pain_points"]),
            strategy["positioning"],
            tuple((name, text) for name, text in strategy["pillars"]),
            _claims_from(strategy["key_messages"]),
        ),
        tuple(
            Angle(
                **{
                    **angle,
                    "key_claims": _claims_from(angle["key_claims"]),
                    "hooks": tuple(Hook(**hook) for hook in angle["hooks"]),
                    "cautions": tuple(angle["cautions"]),
                }
            )
            for angle in data["angles"]
        ),
        tuple(
            PostIdea(
                **{
                    **idea,
                    "outline": tuple(idea["outline"]),
                    "asset_needs": tuple(idea["asset_needs"]),
                    "claims_used": _claims_from(idea["claims_used"]),
                }
            )
            for idea in data["post_ideas"]
        ),
        tuple(AvoidedClaim(**item) for item in data["claims_to_avoid"]),
        tuple(data["warnings"]),
        data["input_tokens"],
        data["output_tokens"],
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
    value: object,
    angles: tuple[Angle, ...],
    quotes: list[str],
    warnings: list[str],
    limit: int,
) -> tuple[PostIdea, ...]:
    known = {a.id: {h.id for h in a.hooks} for a in angles}
    found: list[PostIdea] = []
    for index, item in enumerate(_items(value)[:limit], start=1):
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
