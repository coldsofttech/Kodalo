"""Ask the default AI model once for the copy of one post idea, keep it, and let the user edit it.

The model is sent the chosen idea (its outline, visual concept and the claims it may state), the
chosen hook, the other hooks of its angle and the claims to avoid, and nothing else. It returns the
slide script (or the single image's text), a caption with an alternative opening, alt text and
hashtags. The result is saved for the repository, focus, idea and hook, so it is shown again
instead of asked for again; an edit replaces the saved text and a new request replaces it too.
"""

import json
import re
from dataclasses import asdict, dataclass, replace
from importlib import resources
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.ai import AiConnections
from kodalo.core.repositories.ai.parsers import _reply_json, estimate_tokens
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.repositories.readme import ReadmeService
from kodalo.core.repositories.service import RepoService
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.platforms import PLATFORMS, Platforms, clean_hashtags
from kodalo.core.storage import Database
from kodalo.core.storage.models import StudioCopy
from kodalo.core.studio.ideas import Ideas, IdeasAssistant, PostIdea

MAX_OUTPUT_TOKENS = 4000
_MAX_SLIDES = 12
_FLAG_TYPES = ("needs_review", "assumed_pain", "name_not_available", "other")


@dataclass(frozen=True)
class Slide:
    role: str
    headline: str
    body: str
    visual_note: str
    alt_text: str


@dataclass(frozen=True)
class Caption:
    opening: str
    body: tuple[str, ...]
    cta: str


@dataclass(frozen=True)
class AltOpening:
    text: str
    hook_id: str


@dataclass(frozen=True)
class ReviewFlag:
    type: str
    text: str
    reason: str


@dataclass(frozen=True)
class CopyPlan:
    """What a run would send and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    items: tuple[str, ...]
    input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class PostCopy:
    """The written post: its slides, caption, alternative opening and hashtags."""

    platform: str
    idea_id: str
    hook_id: str
    hook_text: str
    format: str
    slides: tuple[Slide, ...]
    caption: Caption
    alt_opening: AltOpening
    hashtags: tuple[str, ...]
    review_flags: tuple[ReviewFlag, ...]
    warnings: tuple[str, ...]
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Choice:
    """Which idea, written with which hook, for which repository focus and platform."""

    platform: str
    repo_id: str
    post_type: str
    kind: str
    name: str
    idea_id: str
    hook_id: str

    @property
    def key(self) -> str:
        return (
            f"{self.platform}|{self.post_type}|{self.kind}|{self.name}"
            f"|{self.idea_id}|{self.hook_id}"
        )[:600]


def system_prompt(platform: str) -> str:
    """The instructions sent to every provider: the platform's bundled skill file without its
    front matter."""
    folder = resources.files("kodalo.core.ai") / "prompts" / "platforms" / platform
    text = (folder / f"{platform}-copywriter.SKILL.md").read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def _text(value: object, limit: int) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit] if isinstance(value, str) else ""


def _dicts(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _slides(value: object) -> tuple[Slide, ...]:
    return tuple(
        Slide(
            _text(item.get("role"), 16),
            _text(item.get("headline"), 120),
            _text(item.get("body"), 300),
            _text(item.get("visual_note"), 300),
            _text(item.get("alt_text"), 200),
        )
        for item in _dicts(value)[:_MAX_SLIDES]
    )


def _caption(value: object) -> Caption:
    data = value if isinstance(value, dict) else {}
    lines = data.get("body")
    kept = (_text(line, 300) for line in (lines if isinstance(lines, list) else [])[:8])
    return Caption(
        _text(data.get("opening"), 200),
        tuple(line for line in kept if line),
        _text(data.get("cta"), 200),
    )


def _flags(value: object) -> tuple[ReviewFlag, ...]:
    return tuple(
        ReviewFlag(
            item["type"] if item.get("type") in _FLAG_TYPES else "other",
            _text(item.get("text"), 300),
            _text(item.get("reason"), 300),
        )
        for item in _dicts(value)[:20]
    )


def _repeats(post: PostCopy, avoid: tuple[str, ...]) -> tuple[str, ...]:
    parts = [post.caption.opening, post.caption.cta, post.alt_opening.text, *post.caption.body]
    for slide in post.slides:
        parts += [slide.headline, slide.body]
    text = " ".join(parts).casefold()
    return tuple(
        f"The copy repeats a statement to use with care: {claim}"
        for claim in avoid
        if claim and claim.casefold() in text
    )


def _post_from_json(payload: str) -> PostCopy:
    """Rebuild what ``asdict`` wrote when the copy was saved."""
    data = json.loads(payload)
    caption = data["caption"]
    return PostCopy(
        data["platform"],
        data["idea_id"],
        data["hook_id"],
        data["hook_text"],
        data["format"],
        tuple(Slide(**slide) for slide in data["slides"]),
        Caption(caption["opening"], tuple(caption["body"]), caption["cta"]),
        AltOpening(**data["alt_opening"]),
        tuple(data["hashtags"]),
        tuple(ReviewFlag(**flag) for flag in data["review_flags"]),
        tuple(data["warnings"]),
        data["input_tokens"],
        data["output_tokens"],
    )


class CopyAssistant:
    """Builds the input for one idea and runs the single AI request."""

    def __init__(
        self,
        readme: ReadmeService,
        repos: RepoService,
        ideas: IdeasAssistant,
        ai: AiConnections,
        platforms: Platforms,
        database: Database,
    ) -> None:
        self._readme = readme
        self._repos = repos
        self._ideas = ideas
        self._ai = ai
        self._platforms = platforms
        self._database = database

    def _chosen(self, choice: Choice) -> tuple[Ideas, PostIdea, str, str, list[dict[str, str]]]:
        saved = self._ideas.saved(choice.repo_id, choice.post_type, choice.kind, choice.name)
        if saved is None:
            raise RepoNotFoundError("The post ideas were not made yet.")
        idea = next((i for i in saved.post_ideas if i.id == choice.idea_id), None)
        if idea is None:
            raise RepoNotFoundError("That post idea is not in the saved ideas.")
        angle = next((a for a in saved.angles if a.id == idea.angle_id), None)
        hooks = list(angle.hooks) if angle is not None else []
        hook_id = choice.hook_id or idea.hook_id
        hook = next((h for h in hooks if h.id == hook_id), None)
        if hook is None:
            raise AiInvalidError("That hook does not belong to the idea's angle.")
        others = [{"id": h.id, "text": h.text} for h in hooks if h.id != hook.id]
        return saved, idea, hook.id, hook.text, others

    def _request(self, choice: Choice) -> tuple[str, Ideas, PostIdea, str, str]:
        if choice.platform not in PLATFORMS:
            raise AiInvalidError(f"Posts for {choice.platform} cannot be written yet.")
        analysis = self._readme.get(choice.repo_id)
        if analysis is None:
            raise RepoNotFoundError("The README analysis has not been read yet.")
        saved, idea, hook_id, hook_text, others = self._chosen(choice)
        settings = self._platforms.get(choice.platform)
        payload = {
            "product": {
                "name": self._repos.get(choice.repo_id).name,
                "tagline": analysis.tagline,
                "summary": analysis.summary,
            },
            "idea": {
                "format": idea.format,
                "working_title": idea.working_title,
                "objective": idea.objective,
                "outline": list(idea.outline),
                "visual_concept": idea.visual_concept,
                "asset_needs": list(idea.asset_needs),
                "cta_type": idea.cta_type,
                "claims_used": [asdict(c) for c in idea.claims_used],
            },
            "hook": hook_text,
            "alternative_hooks": others,
            "claims_to_avoid": [a.text for a in saved.claims_to_avoid],
            "hashtag_count": max(0, settings.hashtag_count - len(settings.default_hashtags)),
            "default_hashtags": list(settings.default_hashtags),
        }
        return json.dumps(payload, ensure_ascii=False, indent=1), saved, idea, hook_id, hook_text

    @staticmethod
    def _row(session: Session, choice: Choice) -> StudioCopy | None:
        return session.scalars(
            select(StudioCopy).where(
                StudioCopy.repository_id == choice.repo_id, StudioCopy.copy_key == choice.key
            )
        ).first()

    def saved(self, choice: Choice) -> PostCopy | None:
        """The copy kept for this idea and hook, or ``None`` when none was written yet."""
        with self._database.session() as session:
            row = self._row(session, choice)
            return _post_from_json(row.payload) if row is not None else None

    def _save(self, choice: Choice, post: PostCopy) -> None:
        payload = json.dumps(asdict(post), ensure_ascii=False)
        with self._database.session() as session:
            row = self._row(session, choice)
            if row is None:
                session.add(
                    StudioCopy(repository_id=choice.repo_id, copy_key=choice.key, payload=payload)
                )
            else:
                row.payload = payload

    def _hashtags(self, platform: str, written: object) -> tuple[str, ...]:
        """The platform's default hashtags first, then what the AI wrote, up to the total."""
        settings = self._platforms.get(platform)
        return clean_hashtags(
            [*settings.default_hashtags, *clean_hashtags(written)], settings.hashtag_count
        )

    def plan(self, choice: Choice) -> CopyPlan:
        """Work out what would be sent and what asking would cost. Nothing is sent."""
        prompt, _, idea, _, _ = self._request(choice)
        target = self._ai.default_target("studio_copy")
        return CopyPlan(
            target.provider,
            target.label,
            target.model,
            (idea.working_title,),
            estimate_tokens(system_prompt(choice.platform), prompt),
            min(MAX_OUTPUT_TOKENS, target.max_tokens or MAX_OUTPUT_TOKENS),
        )

    def generate(self, choice: Choice) -> PostCopy:
        """Ask the model once, keep what it wrote and return it. Raises ``RepoNotFoundError``
        when the analysis, the ideas or the idea are missing and ``AiInvalidError`` when the
        platform or hook cannot be used or the answer is not in the expected format."""
        prompt, saved, idea, hook_id, hook_text = self._request(choice)
        reply = self._ai.generate(
            system_prompt(choice.platform),
            prompt,
            MAX_OUTPUT_TOKENS,
            purpose="studio",
            title=f"Copy for {idea.working_title} in {choice.repo_id}",
            task="studio_copy",
        )
        data = _reply_json(reply.text)
        slides = _slides(data.get("slides")) if isinstance(data, dict) else ()
        if not slides:
            raise AiInvalidError("The AI did not write the post, so there is no copy.")
        alt = data.get("alt_opening")
        alt = alt if isinstance(alt, dict) else {}
        post = PostCopy(
            choice.platform,
            idea.id,
            hook_id,
            hook_text,
            idea.format,
            slides[:1] if idea.format == "single_image" else slides,
            _caption(data.get("caption")),
            AltOpening(_text(alt.get("text"), 200), _text(alt.get("hook_id"), 64)),
            self._hashtags(choice.platform, data.get("hashtags")),
            _flags(data.get("review_flags")),
            (),
            reply.input_tokens,
            reply.output_tokens,
        )
        post = replace(post, warnings=_repeats(post, tuple(a.text for a in saved.claims_to_avoid)))
        self._save(choice, post)
        return post

    def edit(
        self,
        choice: Choice,
        slides: tuple[Slide, ...],
        caption: Caption,
        alt_opening: str,
        hashtags: tuple[str, ...],
    ) -> PostCopy:
        """Replace the saved text with the user's edits (limits applied). Raises
        ``RepoNotFoundError`` when nothing was written for this idea and hook yet."""
        current = self.saved(choice)
        if current is None:
            raise RepoNotFoundError("No copy was written for this idea yet.")
        post = replace(
            current,
            slides=_slides([asdict(s) for s in slides]),
            caption=_caption(asdict(caption)),
            alt_opening=AltOpening(_text(alt_opening, 200), current.alt_opening.hook_id),
            hashtags=clean_hashtags(list(hashtags)),
        )
        self._save(choice, post)
        return post
