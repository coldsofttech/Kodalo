"""Read a repository's README and the docs it links to, without AI.

The documents come from the repository analysis already stored (the README names and the docs
folder), so nothing that analysis found is fetched again. From their text this finds the purpose,
the documented ways to install and the capabilities. Every item carries a short quote from the
file it came from. Use cases need judgement, so ``ai.readme`` asks for those.
"""

import json
import posixpath
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from typing import Any, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from kodalo.core.repositories.documentation import is_secret
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.repositories.models import RepoInfo
from kodalo.core.repositories.service import RepoService
from kodalo.core.settings.github import GitHubSettings
from kodalo.core.storage import Database
from kodalo.core.storage.models import (
    Repository,
    RepositoryCapability,
    RepositoryDocument,
    RepositoryFeature,
    RepositoryInstall,
    RepositoryReadme,
    RepositoryUseCase,
    utc_now,
)

_T = TypeVar("_T")

MAX_QUOTE = 120
MAX_CAPABILITIES = 30
SKIP_SENSITIVE = "secret"
SKIP_UNREADABLE = "could not be read"
SKIP_NOT_USEFUL = "not about using the product"
SKIP_OVER_LIMIT = "over the document limit"
SKIP_GENERATED = "generated reference"
DOCUMENTED = "documented"
INFERRED = "inferred"

_NOT_USEFUL = ("code_of_conduct", "security", "changelog", "license", "licence", "contributing")
_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>#]+)(?:#[^)\s]*)?[^)]*\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_INSTALL_TITLE = re.compile(r"install|getting started|quick ?start|download|set ?up", re.I)
_FEATURE_TITLE = re.compile(
    r"feature|capabilit|what (it|\w+) (does|can)|highlights|commands?", re.I
)
_PLANNED_TITLE = re.compile(r"roadmap|planned|upcoming|coming soon", re.I)
_CAPABILITY_TITLE = re.compile(f"{_FEATURE_TITLE.pattern}|{_PLANNED_TITLE.pattern}", re.I)
_PLANNED_TEXT = re.compile(r"\b(planned|coming soon|not yet|experimental|roadmap)\b", re.I)
_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_BOLD = re.compile(r"^\*\*([^*]+)\*\*\s*[:\-\u2013\u2014]?\s*(.*)$")
_INSTALLER = re.compile(r"\.(exe|msi|deb|rpm|dmg|pkg)\b|\binstaller\b", re.I)
_METHODS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pipx", re.compile(r"^pipx install\b")),
    ("uv", re.compile(r"^uv (tool install|add|pip install)\b")),
    ("pip", re.compile(r"^(pip3?|python3? -m pip) install\b")),
    ("npm", re.compile(r"^npm (i|install)\b")),
    ("yarn", re.compile(r"^yarn (global )?add\b")),
    ("pnpm", re.compile(r"^pnpm (add|install)\b")),
    ("Homebrew", re.compile(r"^brew (install|tap)\b")),
    ("Scoop", re.compile(r"^scoop (install|bucket add)\b")),
    ("winget", re.compile(r"^winget install\b")),
    ("Chocolatey", re.compile(r"^choco install\b")),
    ("apt", re.compile(r"^(sudo )?apt(-get)? install\b")),
    ("dnf", re.compile(r"^(sudo )?(dnf|yum) install\b")),
    ("Debian package", re.compile(r"^(sudo )?dpkg -i\b")),
    ("RPM package", re.compile(r"^(sudo )?rpm -i")),
    ("cargo", re.compile(r"^cargo install\b")),
    ("go", re.compile(r"^go install\b")),
    ("gem", re.compile(r"^gem install\b")),
    ("Docker", re.compile(r"^docker (pull|run)\b")),
    ("Install script", re.compile(r"^curl\b.*\|\s*(sudo )?(ba)?sh\b")),
    ("From source", re.compile(r"^git clone\b")),
)


@dataclass(frozen=True)
class Evidence:
    """A short quote from a document, and whether it says the thing directly."""

    file: str = ""
    quote: str = ""
    status: str = DOCUMENTED


@dataclass(frozen=True)
class Installation:
    method: str
    command: str = ""
    note: str = ""
    evidence: Evidence = Evidence()


@dataclass(frozen=True)
class Capability:
    name: str
    description: str = ""
    note: str = ""
    evidence: Evidence = Evidence()


IMPORTANCE = ("headline", "supporting", "minor")
MATURITY = ("stable", "experimental", "planned", "unspecified")
CLAIM_TYPES = ("number", "absolute", "comparison", "performance", "compatibility")


@dataclass(frozen=True)
class ClaimFlag:
    """A statement about a feature that should not be repeated without care."""

    type: str
    text: str
    reason: str = ""


@dataclass(frozen=True)
class Feature:
    name: str
    description: str = ""
    evidence: Evidence = Evidence(status=INFERRED)
    importance: str = "supporting"
    maturity: str = "unspecified"
    claims: tuple[ClaimFlag, ...] = ()
    use_cases: tuple[str, ...] = ()


@dataclass(frozen=True)
class UseCase:
    title: str
    description: str = ""
    evidence: Evidence = Evidence(status=INFERRED)


@dataclass(frozen=True)
class Document:
    """A document read (``status`` ``read``) or left out (``skipped``, with the ``reason``)."""

    path: str
    status: str
    reason: str = ""
    size: int = 0


@dataclass(frozen=True)
class ReadmeAnalysis:
    repository_id: str
    tagline: str
    summary: str
    purpose_file: str
    installation: tuple[Installation, ...]
    capabilities: tuple[Capability, ...]
    use_cases: tuple[UseCase, ...]
    documents: tuple[Document, ...]
    warnings: tuple[str, ...]
    analyzed_at: str
    use_cases_at: str | None = None
    features: tuple[Feature, ...] = ()


@dataclass(frozen=True)
class _Section:
    level: int
    title: str
    prose: tuple[str, ...]
    code: tuple[str, ...]


def quote(text: str) -> str:
    """The text on one line, at most ``MAX_QUOTE`` characters."""
    text = " ".join(text.split())
    return text if len(text) <= MAX_QUOTE else text[: MAX_QUOTE - 1] + "…"


def _plain(text: str) -> str:
    """Take the Markdown marks (links, bold, code, images, HTML) out of a line of prose."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(re.sub(r"[*_`]+", "", text).split())


def _sections(text: str) -> list[_Section]:
    """Split Markdown into sections by heading, keeping prose and code lines apart."""
    sections: list[_Section] = []
    level, title = 0, ""
    prose: list[str] = []
    code: list[str] = []
    fenced = False
    for line in re.sub(r"<!--.*?-->", "", text, flags=re.S).splitlines():
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            code.append(line)
            continue
        heading = _HEADING.match(line)
        if heading:
            sections.append(_Section(level, title, tuple(prose), tuple(code)))
            level, title = len(heading.group(1)), _plain(heading.group(2))
            prose, code = [], []
        else:
            prose.append(line)
    sections.append(_Section(level, title, tuple(prose), tuple(code)))
    return [s for s in sections if s.prose or s.code or s.title]


def _in_sections(sections: list[_Section], title: re.Pattern[str]) -> list[_Section]:
    """The sections whose heading matches, plus the deeper ones that follow them."""
    found: list[_Section] = []
    parent = 0
    for section in sections:
        if parent and section.level > parent:
            found.append(section)
        elif title.search(section.title):
            parent = section.level
            found.append(section)
        else:
            parent = 0
    return found


def purpose(text: str) -> tuple[str, str]:
    """The tagline (first sentence) and the summary (first paragraph) of a README."""
    paragraph: list[str] = []
    for section in _sections(text):
        for line in section.prose:
            line = line.strip()
            plain = _plain(line)
            if not plain or line.startswith(("|", ">", "---", "===")) or _BULLET.match(line):
                if paragraph:
                    break
                continue
            if re.match(r"^\W*(badge|build|license)\W*$", plain, re.I):
                continue
            paragraph.append(plain)
        if paragraph:
            break
    summary = " ".join(paragraph)
    first = re.split(r"(?<=[.!?])\s", summary, maxsplit=1)[0] if summary else ""
    return first[:256], summary[:1000]


def installation(path: str, text: str) -> list[Installation]:
    """The install commands in the install sections of one document."""
    found: list[Installation] = []
    for section in _in_sections(_sections(text), _INSTALL_TITLE):
        for raw in section.code:
            line = raw.strip().removeprefix("$ ").removeprefix("> ").strip()
            for method, pattern in _METHODS:
                if pattern.match(line):
                    found.append(Installation(method, line[:512], "", Evidence(path, quote(line))))
                    break
        for raw in section.prose:
            plain = _plain(raw)
            if plain and _INSTALLER.search(plain) and len(plain) < 300:
                found.append(Installation("Installer", "", "", Evidence(path, quote(plain))))
                break
    return found


def capabilities(path: str, text: str) -> list[Capability]:
    """The bullets under the feature, command and roadmap headings of one document."""
    found: list[Capability] = []
    for section in _in_sections(_sections(text), _CAPABILITY_TITLE):
        planned = bool(_PLANNED_TITLE.search(section.title))
        for line in section.prose:
            bullet = _BULLET.match(line)
            if not bullet:
                continue
            item = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", bullet.group(1)).strip()
            bold = _BOLD.match(item)
            if bold:
                name, description = _plain(bold.group(1)), _plain(bold.group(2))
            else:
                name, description = _split(_plain(item))
            if not name or len(name) > 128:
                continue
            note = "Planned or experimental" if planned or _PLANNED_TEXT.search(item) else ""
            found.append(
                Capability(name, description[:512], note, Evidence(path, quote(f"- {item}")))
            )
    return found


def _split(text: str) -> tuple[str, str]:
    """Split ``Name: description`` or ``Name - description``; else the first words are the name."""
    parts = re.split(r"\s*(?::|\s[-\u2013\u2014]\s)\s*", text, maxsplit=1)
    if len(parts) == 2 and len(parts[0].split()) <= 8:
        return parts[0], parts[1]
    words = text.split()
    return " ".join(words[:8]), " ".join(words[8:])


def linked_documents(path: str, text: str) -> list[str]:
    """The relative Markdown files a document links to, as paths from the repository root."""
    base = posixpath.dirname(path)
    found: dict[str, None] = {}
    for target in _LINK.findall(text):
        if "://" in target or target.startswith(("mailto:", "/")):
            continue
        if not target.lower().endswith((".md", ".markdown")):
            continue
        resolved = posixpath.normpath(posixpath.join(base, target))
        if not resolved.startswith(".."):
            found[resolved] = None
    return list(found)


def _skip_reason(path: str) -> str:
    name = posixpath.basename(path).lower()
    if is_secret(path):
        return SKIP_SENSITIVE
    if any(name.startswith(prefix) for prefix in _NOT_USEFUL):
        return SKIP_NOT_USEFUL
    if "reference" in name:
        return SKIP_GENERATED
    return ""


class ReadmeService:
    """Reads, keeps and returns the README analysis of a stored repository."""

    def __init__(self, database: Database, repos: RepoService) -> None:
        self._database = database
        self._repos = repos

    def get(self, repo_id: str) -> ReadmeAnalysis | None:
        """The saved analysis, or ``None`` when the repository was not analyzed yet."""
        with self._database.session() as session:
            row = session.scalars(
                select(RepositoryReadme).where(RepositoryReadme.repository_id == repo_id)
            ).first()
            if row is None:
                return None
            return _analysis(session, row)

    def read(
        self, settings: GitHubSettings, repo_id: str, *, refresh: bool = False
    ) -> ReadmeAnalysis:
        """Return the saved analysis; read the documents when there is none or ``refresh``."""
        saved = self.get(repo_id)
        if not refresh and saved is not None:
            return saved
        info = self._repos.get(repo_id)
        texts, documents, warnings = self._documents(settings, info)
        tagline = summary = purpose_file = ""
        installs: list[Installation] = []
        capable: list[Capability] = []
        for path, text in texts.items():
            if not tagline and path in info.documentation.readmes:
                tagline, summary = purpose(text)
                purpose_file = path
            installs += installation(path, text)
            capable += capabilities(path, text)
        if not summary and info.description:
            tagline, summary, purpose_file = info.description[:256], info.description, ""
            warnings.append(
                "The README has no introduction, so the repository description is used."
            )
        if not texts:
            warnings.append("No README or document could be read.")
        installs = _unique(installs, lambda i: (i.method, i.command))
        capable = _unique(capable, lambda c: c.name.lower())[:MAX_CAPABILITIES]
        if saved is not None and saved.use_cases_at is not None:
            # The AI has already written this analysis: keep it and only add what is new.
            if saved.summary:
                tagline, summary, purpose_file = saved.tagline, saved.summary, saved.purpose_file
            known = {(i.method.lower(), i.command.lower()) for i in saved.installation}
            installs = [
                *saved.installation,
                *(i for i in installs if (i.method.lower(), i.command.lower()) not in known),
            ]
            # The AI picked which capabilities matter, so the plain read adds none of its own; it
            # only fills in what the AI left blank for a capability with the same name.
            found = {c.name.lower(): c for c in capable}
            capable = [
                replace(c, description=c.description or found[c.name.lower()].description)
                if c.name.lower() in found
                else c
                for c in saved.capabilities
            ]
        return self._save(
            repo_id, tagline, summary, purpose_file, installs, capable, documents, warnings
        )

    def _documents(
        self, settings: GitHubSettings, info: RepoInfo
    ) -> tuple[dict[str, str], list[Document], list[str]]:
        """Read the README files, then the docs they link to one level deep, up to the limit."""
        texts: dict[str, str] = {}
        documents: list[Document] = []
        warnings: list[str] = []
        queue = list(info.documentation.readmes)
        linked: list[str] = []
        seen: set[str] = set()
        max_bytes = settings.document_max_kb * 1024
        while queue or linked:
            if not queue:
                docs = info.documentation.docs_dir.lower() + "/"
                queue = sorted(linked, key=lambda p: not p.lower().startswith(docs))
                linked = []
            path = queue.pop(0)
            if path in seen:
                continue
            seen.add(path)
            reason = "" if path in info.documentation.readmes else _skip_reason(path)
            if not reason and len(texts) >= settings.document_limit:
                reason = SKIP_OVER_LIMIT
            text = None if reason else self._repos.read_text(settings, info, path)
            if text is None:
                documents.append(Document(path, "skipped", reason or SKIP_UNREADABLE))
                continue
            size = len(text.encode("utf-8"))
            if size > max_bytes:
                text = text.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
                warnings.append(
                    f"{path} is larger than {settings.document_max_kb} KB; the rest was not read."
                )
            texts[path] = text
            documents.append(Document(path, "read", "", size))
            if path in info.documentation.readmes:
                linked += [p for p in linked_documents(path, text) if p not in seen]
        return texts, documents, warnings

    def _save(
        self,
        repo_id: str,
        tagline: str,
        summary: str,
        purpose_file: str,
        installs: list[Installation],
        capable: list[Capability],
        documents: list[Document],
        warnings: list[str],
    ) -> ReadmeAnalysis:
        with self._database.session() as session:
            if session.get(Repository, repo_id) is None:
                raise RepoNotFoundError("That repository is not stored.")
            previous = session.scalars(
                select(RepositoryReadme).where(RepositoryReadme.repository_id == repo_id)
            ).first()
            use_cases_at = previous.use_cases_at if previous else None
            _clear(session, repo_id)
            session.flush()
            row = RepositoryReadme(
                repository_id=repo_id,
                tagline=tagline,
                summary=summary,
                purpose_file=purpose_file,
                warnings_json=json.dumps(warnings),
                analyzed_at=utc_now(),
                use_cases_at=use_cases_at,
            )
            session.add(row)
            session.add_all(
                RepositoryDocument(
                    repository_id=repo_id,
                    path=d.path,
                    status=d.status,
                    reason=d.reason,
                    size=d.size,
                    position=n,
                )
                for n, d in enumerate(documents)
            )
            session.add_all(
                RepositoryInstall(
                    repository_id=repo_id,
                    method=i.method,
                    command=i.command,
                    note=i.note,
                    file=i.evidence.file,
                    quote=i.evidence.quote,
                    status=i.evidence.status,
                    position=n,
                )
                for n, i in enumerate(installs)
            )
            session.add_all(
                RepositoryCapability(
                    repository_id=repo_id,
                    name=c.name,
                    description=c.description,
                    note=c.note,
                    file=c.evidence.file,
                    quote=c.evidence.quote,
                    status=c.evidence.status,
                    position=n,
                )
                for n, c in enumerate(capable)
            )
            session.flush()
            return _analysis(session, row)

    def texts(self, settings: GitHubSettings, repo_id: str) -> dict[str, str]:
        """Read the documents the analysis read, again, with the document size limit."""
        info = self._repos.get(repo_id)
        analysis = self.get(repo_id)
        if analysis is None:
            raise RepoNotFoundError("The README analysis has not been read yet.")
        max_bytes = settings.document_max_kb * 1024
        texts: dict[str, str] = {}
        for document in analysis.documents:
            if document.status != "read":
                continue
            text = self._repos.read_text(settings, info, document.path)
            if text is not None:
                texts[document.path] = text.encode("utf-8")[:max_bytes].decode(
                    "utf-8", errors="ignore"
                )
        return texts

    def save_ai(
        self,
        repo_id: str,
        purpose: tuple[str, str, str] | None,
        installs: list[Installation] | None,
        capable: list[Capability] | None,
        use_cases: list[UseCase] | None,
        features: list[Feature] | None = None,
    ) -> ReadmeAnalysis:
        """Replace the parts the AI wrote; ``None`` keeps a part as it was."""
        with self._database.session() as session:
            row = session.scalars(
                select(RepositoryReadme).where(RepositoryReadme.repository_id == repo_id)
            ).first()
            if row is None:
                raise RepoNotFoundError("The README analysis has not been read yet.")
            if purpose is not None:
                row.tagline, row.summary, row.purpose_file = purpose
            if installs is not None:
                session.execute(delete(RepositoryInstall).where(_of(RepositoryInstall, repo_id)))
                session.add_all(
                    RepositoryInstall(
                        repository_id=repo_id,
                        method=i.method,
                        command=i.command,
                        note=i.note,
                        file=i.evidence.file,
                        quote=i.evidence.quote,
                        status=i.evidence.status,
                        position=n,
                    )
                    for n, i in enumerate(installs)
                )
            if capable is not None:
                session.execute(
                    delete(RepositoryCapability).where(_of(RepositoryCapability, repo_id))
                )
                session.add_all(
                    RepositoryCapability(
                        repository_id=repo_id,
                        name=c.name,
                        description=c.description,
                        note=c.note,
                        file=c.evidence.file,
                        quote=c.evidence.quote,
                        status=c.evidence.status,
                        position=n,
                    )
                    for n, c in enumerate(capable)
                )
            if features is not None:
                session.execute(delete(RepositoryFeature).where(_of(RepositoryFeature, repo_id)))
                session.add_all(
                    RepositoryFeature(
                        repository_id=repo_id,
                        name=f.name,
                        description=f.description,
                        file=f.evidence.file,
                        quote=f.evidence.quote,
                        status=f.evidence.status,
                        importance=f.importance,
                        maturity=f.maturity,
                        claims_json=json.dumps([asdict(c) for c in f.claims]),
                        use_cases_json=json.dumps(list(f.use_cases)),
                        position=n,
                    )
                    for n, f in enumerate(features)
                )
            if use_cases is not None:
                session.execute(delete(RepositoryUseCase).where(_of(RepositoryUseCase, repo_id)))
                session.add_all(
                    RepositoryUseCase(
                        repository_id=repo_id,
                        title=u.title,
                        description=u.description,
                        file=u.evidence.file,
                        quote=u.evidence.quote,
                        status=u.evidence.status,
                        position=n,
                    )
                    for n, u in enumerate(use_cases)
                )
            row.use_cases_at = utc_now()
            session.flush()
            session.expire_all()
            return _analysis(session, row)


def _of(model: Any, repo_id: str) -> Any:
    return model.repository_id == repo_id


def _clear(session: Session, repo_id: str) -> None:
    """Remove the README row and what the deterministic read makes. Features and use cases stay."""
    for model in (RepositoryReadme, RepositoryDocument, RepositoryInstall, RepositoryCapability):
        session.execute(delete(model).where(model.repository_id == repo_id))


def _unique(items: list[_T], key: Callable[[_T], object]) -> list[_T]:
    """Keep the first of the items that share a key, in order."""
    return list({key(item): item for item in reversed(items)}.values())[::-1]


def _analysis(session: Session, row: RepositoryReadme) -> ReadmeAnalysis:
    repo_id = row.repository_id
    installs = session.scalars(
        select(RepositoryInstall)
        .where(RepositoryInstall.repository_id == repo_id)
        .order_by(RepositoryInstall.position)
    ).all()
    capable = session.scalars(
        select(RepositoryCapability)
        .where(RepositoryCapability.repository_id == repo_id)
        .order_by(RepositoryCapability.position)
    ).all()
    featured = session.scalars(
        select(RepositoryFeature)
        .where(RepositoryFeature.repository_id == repo_id)
        .order_by(RepositoryFeature.position)
    ).all()
    cases = session.scalars(
        select(RepositoryUseCase)
        .where(RepositoryUseCase.repository_id == repo_id)
        .order_by(RepositoryUseCase.position)
    ).all()
    documents = session.scalars(
        select(RepositoryDocument)
        .where(RepositoryDocument.repository_id == repo_id)
        .order_by(RepositoryDocument.position)
    ).all()
    return ReadmeAnalysis(
        repository_id=repo_id,
        tagline=row.tagline,
        summary=row.summary,
        purpose_file=row.purpose_file,
        installation=tuple(
            Installation(r.method, r.command, r.note, Evidence(r.file, r.quote, r.status))
            for r in installs
        ),
        capabilities=tuple(
            Capability(r.name, r.description, r.note, Evidence(r.file, r.quote, r.status))
            for r in capable
        ),
        use_cases=tuple(
            UseCase(r.title, r.description, Evidence(r.file, r.quote, r.status)) for r in cases
        ),
        documents=tuple(Document(r.path, r.status, r.reason, r.size) for r in documents),
        warnings=tuple(json.loads(row.warnings_json)),
        analyzed_at=row.analyzed_at or "",
        use_cases_at=row.use_cases_at,
        features=tuple(
            Feature(
                r.name,
                r.description,
                Evidence(r.file, r.quote, r.status),
                r.importance,
                r.maturity,
                tuple(ClaimFlag(**c) for c in json.loads(r.claims_json)),
                tuple(json.loads(r.use_cases_json)),
            )
            for r in featured
        ),
    )
