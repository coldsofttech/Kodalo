"""Read repositories the way the GitHub setting says, and keep what was read in the database."""

import json
import os
import re
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.repositories.configs.framework import (
    FrameworkConfigSet,
    detect_frameworks,
    detect_tooling,
    load_framework_configs,
    load_tooling_configs,
)
from kodalo.core.repositories.configs.manifest import (
    ConfigSet,
    load_configs,
    manifest_rules,
    match_config,
)
from kodalo.core.repositories.documentation import find_documentation, is_secret
from kodalo.core.repositories.errors import RepoDetailsError, RepoNotFoundError
from kodalo.core.repositories.icon import (
    MAX_ICON_BYTES,
    icon_candidates,
    icon_type,
)
from kodalo.core.repositories.layout import (
    MAX_MANIFESTS,
    DirectoryRule,
    LayoutRules,
    SignalRule,
    analyze,
    without_ignored,
)
from kodalo.core.repositories.models import (
    Documentation,
    Entry,
    Framework,
    Language,
    Layout,
    LocalDetails,
    Manifest,
    NotableDir,
    RepoInfo,
    SkippedFile,
)
from kodalo.core.repositories.parsers.manifest import parse_manifest
from kodalo.core.repositories.readers.github import Fetch, gh_fetch, read_github, web_fetch
from kodalo.core.repositories.readers.github import read_bytes as _read_github_bytes
from kodalo.core.repositories.readers.github import read_file as read_github_file
from kodalo.core.repositories.readers.local import read_bytes as _read_local_bytes
from kodalo.core.repositories.readers.local import read_file as read_local_file
from kodalo.core.repositories.readers.local import read_local
from kodalo.core.repositories.social_preview import PreviewFetch, gh_social_preview, image_type
from kodalo.core.settings.github import GitHubSettings
from kodalo.core.storage import Database
from kodalo.core.storage.models import (
    DirectoryPattern,
    IgnoredDirectory,
    MonorepoSignal,
    Repository,
    RepositoryDependency,
    RepositoryEntry,
    RepositoryFramework,
    RepositoryLanguage,
    RepositoryManifest,
    RepositoryNotableDir,
    RepositoryTool,
    RepositoryTopic,
    utc_now,
)
from kodalo.core.studio import Source

MAX_EVIDENCE = 120
SKIP_SENSITIVE = "secret"
SKIP_UNREADABLE = "too large or unreadable"  # over 200 KB, binary, or the read failed


def _box(text: str) -> tuple[float, float, float, float] | None:
    """The logo's box from its saved JSON, or ``None`` when there is none or it is not valid."""
    try:
        x, y, w, h = (float(v) for v in json.loads(text or "[]"))
    except (ValueError, TypeError):
        return None
    return (x, y, w, h)


def _info(row: Repository) -> RepoInfo:
    return RepoInfo(
        id=row.id,
        url=row.url,
        owner=row.owner,
        name=row.name,
        description=row.description,
        homepage=row.homepage,
        default_branch=row.default_branch,
        license=row.license,
        topics=tuple(topic.name for topic in row.topics),
        is_private=row.is_private,
        is_fork=row.is_fork,
        is_archived=row.is_archived,
        last_pushed_at=row.last_pushed_at,
        languages=tuple(Language(lang.name, lang.bytes, lang.percent) for lang in row.languages),
        top_level=tuple(Entry(e.path, e.type) for e in row.entries),
        file_count=row.file_count,
        access_method=row.access_method,
        tree_truncated=row.tree_truncated,
        warnings=tuple(json.loads(row.warnings_json)),
        local_path=row.local_path,
        last_scanned_at=row.last_scanned_at,
        icon_candidates=tuple(json.loads(row.icon_candidates_json)),
        icon_path=row.icon_path,
        icon_checked_at=row.icon_checked_at,
        icon_box=_box(row.icon_box_json),
        icon_box_checked=row.icon_box_json != "",
        notable_dirs=tuple(NotableDir(d.path, d.purpose, d.pattern_id) for d in row.notable_dirs),
        manifests=tuple(_manifest(m) for m in row.manifests),
        is_monorepo=row.is_monorepo,
        monorepo_signals=tuple(json.loads(row.monorepo_signals_json)),
        frameworks=tuple(
            Framework(f.framework_id, f.name, f.category, f.evidence, f.path)
            for f in row.frameworks
        ),
        tooling=tuple(
            Framework(t.tool_id, t.name, t.category, t.evidence, t.path) for t in row.tooling
        ),
        documentation=_documentation(row.documentation_json),
        skipped=tuple(SkippedFile(s["path"], s["reason"]) for s in json.loads(row.skipped_json)),
    )


def _documentation(text: str) -> Documentation:
    data = json.loads(text)
    return Documentation(**{**data, "readmes": tuple(data.get("readmes", ()))})


def _manifest(row: RepositoryManifest) -> Manifest:
    return Manifest(
        evidence=row.evidence,
        path=row.path,
        ecosystem=row.ecosystem,
        is_lockfile=row.is_lockfile,
        package_name=row.package_name,
        version=row.version,
        dependencies=tuple(d.name for d in row.dependencies if not d.is_dev),
        dev_dependencies=tuple(d.name for d in row.dependencies if d.is_dev),
    )


def _rules(session: Session, configs: ConfigSet) -> LayoutRules:
    patterns = session.scalars(select(DirectoryPattern).order_by(DirectoryPattern.sort_order))
    signals = session.scalars(select(MonorepoSignal).order_by(MonorepoSignal.id))
    return LayoutRules(
        directories=tuple(
            DirectoryRule(p.id, p.name, p.purpose, p.match_kind, p.max_depth) for p in patterns
        ),
        signals=tuple(
            SignalRule(s.ecosystem, s.signal_kind, s.file_name, s.min_count) for s in signals
        ),
        manifests=manifest_rules(configs.configs),
        ignored=frozenset(d.name.lower() for d in session.scalars(select(IgnoredDirectory))),
    )


def _manifest_row(manifest: Manifest) -> RepositoryManifest:
    names = [(n, False) for n in manifest.dependencies]
    names += [(n, True) for n in manifest.dev_dependencies]
    return RepositoryManifest(
        path=manifest.path,
        ecosystem=manifest.ecosystem,
        is_lockfile=manifest.is_lockfile,
        package_name=manifest.package_name,
        version=manifest.version,
        evidence=manifest.evidence,
        dependencies=[
            RepositoryDependency(name=name, is_dev=is_dev, position=position)
            for position, (name, is_dev) in enumerate(names)
        ],
    )


def _read_details(
    layout: Layout,
    configs: ConfigSet,
    read: Callable[[str], str | None],
    limit: int,
) -> tuple[Layout, list[str], list[SkippedFile]]:
    """Read up to ``limit`` project files, top folders first, and add what they say.

    Files that look like secrets are never opened; files that cannot be read (too large, binary,
    or failing) are recorded too, so the result says what was left out.
    """
    projects = sorted(
        (m for m in layout.manifests if not m.is_lockfile),
        key=lambda m: (m.path.count("/"), m.path.lower()),
    )
    chosen = projects[:limit]
    notes: list[str] = []
    if len(projects) > len(chosen):
        notes.append(
            f"Only {len(chosen)} of {len(projects)} project files were read. "
            "Raise the limit in Settings to read more."
        )
    details: dict[str, Manifest] = {}
    skipped: list[SkippedFile] = []
    for manifest in chosen:
        matched = match_config(manifest.path, configs.configs)
        if matched is None:
            continue
        if is_secret(manifest.path):
            skipped.append(SkippedFile(manifest.path, SKIP_SENSITIVE))
            continue
        text = read(manifest.path)
        if text is None:
            skipped.append(SkippedFile(manifest.path, SKIP_UNREADABLE))
            continue
        parsed = parse_manifest(text, matched[0])
        notes += [f"{manifest.path} {warning}" for warning in parsed.warnings]
        details[manifest.path] = replace(
            manifest,
            package_name=parsed.package_name,
            version=parsed.version,
            dependencies=parsed.dependencies,
            dev_dependencies=parsed.dev_dependencies,
            evidence=_quote(text, parsed.package_name or next(iter(parsed.dependencies), None)),
        )
    unread = sum(1 for s in skipped if s.reason == SKIP_UNREADABLE)
    if unread:
        notes.append(f"{unread} project file(s) could not be read.")
    merged = tuple(details.get(m.path, m) for m in layout.manifests)
    return replace(layout, manifests=merged), notes, skipped


_T = TypeVar("_T")


def _attempt(label: str, failures: list[str], empty: _T, run: Callable[[], _T]) -> _T:
    """Run one detection step; when it fails, note it in ``failures`` and return ``empty``."""
    try:
        return run()
    except Exception:
        failures.append(f"{label} could not be detected, so that part is missing.")
        return empty


def _quote(text: str, needle: str | None) -> str:
    """The first line that holds ``needle``, trimmed to 120 characters; empty when none does."""
    if not needle:
        return ""
    whole = re.compile(rf"(?<![\w.-]){re.escape(needle)}(?![\w.-])")
    for line in text.splitlines():
        if whole.search(line):
            return line.strip()[:MAX_EVIDENCE]
    return ""


def _stored_file(directory: Path, repo_id: str, extension: str) -> Path:
    """The file ``<repo_id>.<extension>`` in ``directory``. An id that would leave the folder is
    treated as an unknown repository."""
    root = os.path.normpath(directory)
    full = os.path.normpath(os.path.join(root, f"{repo_id}.{extension}"))
    if not full.startswith(root + os.sep):
        raise RepoNotFoundError("No repository has that id.")
    return Path(full)


class RepoService:
    """Repositories kept in the local database."""

    def __init__(
        self,
        database: Database,
        *,
        gh: Fetch = gh_fetch,
        web: Fetch = web_fetch,
        parsers_dir: Path | None = None,
        frameworks_dir: Path | None = None,
        tooling_dir: Path | None = None,
        previews_dir: Path | None = None,
        preview: PreviewFetch = gh_social_preview,
        icons_dir: Path | None = None,
    ) -> None:
        self._database = database
        self._parsers_dir = parsers_dir
        self._frameworks_dir = frameworks_dir
        self._tooling_dir = tooling_dir
        self._previews_dir = previews_dir
        self._icons_dir = icons_dir
        self._preview = preview
        self._gh = gh
        self._web = web

    # Reading from the database

    def list_repos(self) -> list[RepoInfo]:
        """Return every stored repository, sorted by owner and name."""
        with self._database.session() as session:
            rows = session.scalars(select(Repository)).all()
            infos = sorted(
                (_info(r) for r in rows), key=lambda i: (i.owner.lower(), i.name.lower())
            )
        return [self._shown(i) for i in infos]

    def get(self, repo_id: str) -> RepoInfo:
        with self._database.session() as session:
            row = session.get(Repository, repo_id)
            if row is None:
                raise RepoNotFoundError("That repository is not stored.")
            return self._shown(_info(row))

    def remove(self, repo_id: str) -> None:
        """Delete a stored repository with everything saved about it."""
        with self._database.session() as session:
            row = session.get(Repository, repo_id)
            if row is None:
                raise RepoNotFoundError("That repository is not stored.")
            session.delete(row)
        self._forget_preview(repo_id)

    def stored(self, source: Source) -> RepoInfo | None:
        """Return the stored repository for ``source``, if it was read before."""
        with self._database.session() as session:
            row = self._find(session, source)
            return self._shown(_info(row)) if row is not None else None

    def social_preview(self, repo_id: str) -> tuple[Path, str] | None:
        """Return the saved social preview image and its media type, if there is one."""
        if self._previews_dir is None:
            return None
        for extension, media_type in (("png", "image/png"), ("jpg", "image/jpeg")):
            path = _stored_file(self._previews_dir, repo_id, extension)
            if path.is_file():
                return path, media_type
        return None

    def icon(self, repo_id: str) -> tuple[Path, str] | None:
        """Return the saved icon file and its media type, if there is one."""
        if self._icons_dir is None:
            return None
        kinds = (
            ("png", "image/png"),
            ("jpg", "image/jpeg"),
            ("webp", "image/webp"),
            ("svg", "image/svg+xml"),
        )
        for extension, media_type in kinds:
            path = _stored_file(self._icons_dir, repo_id, extension)
            if path.is_file():
                return path, media_type
        return None

    def save_icon(self, repo_id: str, path: str, data: bytes | None) -> bool:
        """Keep the icon the README analysis picked (``path`` in the repository, its bytes in
        ``data``), or note that none was found when ``data`` is ``None`` or not an image. Returns
        whether an icon was kept."""
        kind = icon_type(data) if data and len(data) <= MAX_ICON_BYTES else None
        if self._icons_dir is not None:
            for extension in ("png", "jpg", "webp", "svg"):
                _stored_file(self._icons_dir, repo_id, extension).unlink(missing_ok=True)
            if data and kind:
                self._icons_dir.mkdir(parents=True, exist_ok=True)
                _stored_file(self._icons_dir, repo_id, kind).write_bytes(data)
            else:
                kind = None
        else:
            kind = None
        with self._database.session() as session:
            row = session.get(Repository, repo_id)
            if row is None:
                raise RepoNotFoundError("That repository is not stored.")
            row.icon_path = path if kind else ""
            row.icon_ext = kind or ""
            row.icon_checked_at = utc_now()
        return kind is not None

    def save_icon_box(self, repo_id: str, box: tuple[float, float, float, float] | None) -> None:
        """Keep where the logo is in the social preview, or that there is none."""
        with self._database.session() as session:
            row = session.get(Repository, repo_id)
            if row is None:
                raise RepoNotFoundError("That repository is not stored.")
            row.icon_box_json = json.dumps(list(box) if box else [])

    def read_bytes(self, settings: GitHubSettings, info: RepoInfo, path: str) -> bytes | None:
        """Return the bytes of one file of a stored repository, or ``None`` when unreadable."""
        if info.local_path:
            return _read_local_bytes(Path(info.local_path), path, MAX_ICON_BYTES)
        fetch = self._gh if settings.mode == "gh_cli" else self._web
        return _read_github_bytes(fetch, info.owner, info.name, path, MAX_ICON_BYTES)

    def _shown(self, info: RepoInfo) -> RepoInfo:
        return replace(
            info,
            has_social_preview=self.social_preview(info.id) is not None,
            has_icon=self.icon(info.id) is not None,
        )

    def _forget_preview(self, repo_id: str) -> None:
        if self._previews_dir is None:
            return
        for extension in ("png", "jpg"):
            _stored_file(self._previews_dir, repo_id, extension).unlink(missing_ok=True)

    def _save_preview(self, info: RepoInfo) -> None:
        """Keep the owner's social preview, or drop an old one that is gone. Never fails."""
        if self._previews_dir is None:
            return
        try:
            data = self._preview(info.owner, info.name)
            kind = image_type(data) if data else None
            self._forget_preview(info.id)
            if data and kind:
                self._previews_dir.mkdir(parents=True, exist_ok=True)
                _stored_file(self._previews_dir, info.id, kind).write_bytes(data)
        except OSError:
            return

    def configs(self) -> ConfigSet:
        """Return the parser configs in use: the bundled ones and the user's own."""
        return load_configs(self._parsers_dir)

    def framework_configs(self) -> FrameworkConfigSet:
        """Return the framework configs in use: the bundled ones and the user's own."""
        return load_framework_configs(self._frameworks_dir)

    def tooling_configs(self) -> FrameworkConfigSet:
        """Return the tooling configs in use: the bundled ones and the user's own."""
        return load_tooling_configs(self._tooling_dir)

    def read_text(self, settings: GitHubSettings, info: RepoInfo, path: str) -> str | None:
        """Return the text of one file of a stored repository, or ``None`` when unreadable."""
        if info.local_path:
            return read_local_file(Path(info.local_path), path)
        fetch = self._gh if settings.mode == "gh_cli" else self._web
        return read_github_file(fetch, info.owner, info.name, path)

    # Reading from GitHub or a folder

    def read(
        self,
        settings: GitHubSettings,
        source: Source,
        details: LocalDetails | None = None,
        *,
        refresh: bool = False,
    ) -> RepoInfo:
        """Return the stored repository, or read and store it when new or when ``refresh``."""
        stored = self.stored(source)
        if stored is not None and not refresh:
            return stored
        if source.kind == "local_folder":
            info = read_local(Path(source.value), details or self._details(stored))
        else:
            fetch = self._gh if settings.mode == "gh_cli" else self._web
            info = read_github(source.owner, source.repo, fetch, settings.mode)
        configs = load_configs(self._parsers_dir)
        with self._database.session() as session:
            rules = _rules(session, configs)
        layout = analyze(info.paths, rules)
        if source.kind == "local_folder":
            reader: Callable[[str], str | None] = lambda path: read_local_file(  # noqa: E731
                Path(info.local_path), path
            )
            limit = MAX_MANIFESTS
        else:
            reader = lambda path: read_github_file(  # noqa: E731
                fetch, info.owner, info.name, path
            )
            limit = settings.manifest_limit
        layout, notes, skipped = _read_details(layout, configs, reader, limit)
        frameworks = load_framework_configs(self._frameworks_dir)
        kept = without_ignored(info.paths, rules.ignored)
        tools = load_tooling_configs(self._tooling_dir)
        failures: list[str] = []
        found = _attempt(
            "Frameworks",
            failures,
            info.frameworks,
            lambda: detect_frameworks(frameworks.rules, layout.manifests, kept),
        )
        tooling = _attempt(
            "Tooling",
            failures,
            info.tooling,
            lambda: detect_tooling(tools.rules, layout.manifests, kept),
        )
        documentation = _attempt(
            "Documentation", failures, info.documentation, lambda: find_documentation(info.paths)
        )
        info = replace(
            info,
            warnings=(
                *info.warnings,
                *configs.problems,
                *frameworks.problems,
                *tools.problems,
                *notes,
                *failures,
            ),
            frameworks=found,
            tooling=tooling,
            documentation=documentation,
            skipped=tuple(skipped),
        )
        saved = self._save(info, layout)
        if source.kind != "local_folder" and settings.mode == "gh_cli":
            self._save_preview(saved)
        return self._shown(saved)

    @staticmethod
    def _details(stored: RepoInfo | None) -> LocalDetails:
        if stored is None:
            raise RepoDetailsError(
                "Please fill in: owner, repository name, license, default branch."
            )
        return LocalDetails(
            owner=stored.owner,
            repo=stored.name,
            license=stored.license or "",
            default_branch=stored.default_branch or "",
            description=stored.description,
            homepage=stored.homepage,
            topics=stored.topics,
            is_private=stored.is_private,
            is_fork=stored.is_fork,
            is_archived=stored.is_archived,
        )

    @staticmethod
    def _find(session: Session, source: Source) -> Repository | None:
        if source.kind == "local_folder":
            query = select(Repository).where(Repository.local_path == source.value)
        else:
            query = select(Repository).where(Repository.url == source.value)
        return session.scalars(query).first()

    def _save(self, info: RepoInfo, layout: Layout) -> RepoInfo:
        with self._database.session() as session:
            row = session.scalars(select(Repository).where(Repository.url == info.url)).first()
            if row is None:
                row = Repository(url=info.url)
                session.add(row)
            row.owner = info.owner
            row.name = info.name
            row.description = info.description
            row.homepage = info.homepage
            row.default_branch = info.default_branch
            row.license = info.license
            row.is_private = info.is_private
            row.is_fork = info.is_fork
            row.is_archived = info.is_archived
            row.last_pushed_at = info.last_pushed_at
            row.access_method = info.access_method
            row.tree_truncated = info.tree_truncated
            row.file_count = info.file_count
            row.warnings_json = json.dumps(list(info.warnings))
            row.local_path = info.local_path
            row.documentation_json = json.dumps(asdict(info.documentation))
            row.skipped_json = json.dumps([asdict(s) for s in info.skipped])
            row.icon_candidates_json = json.dumps(list(icon_candidates(info.paths)))
            row.last_scanned_at = utc_now()
            row.languages.clear()
            row.topics.clear()
            row.entries.clear()
            row.notable_dirs.clear()
            row.manifests.clear()
            row.frameworks.clear()
            row.tooling.clear()
            session.flush()  # remove the old rows before adding rows with the same names
            row.topics = [
                RepositoryTopic(name=name, position=position)
                for position, name in enumerate(dict.fromkeys(info.topics))
            ]
            row.entries = [
                RepositoryEntry(path=entry.path, type=entry.type, position=position)
                for position, entry in enumerate(info.top_level)
            ]
            row.languages = [
                RepositoryLanguage(name=lang.name, bytes=lang.bytes, percent=lang.percent)
                for lang in info.languages
            ]
            row.is_monorepo = layout.is_monorepo
            row.monorepo_signals_json = json.dumps(list(layout.monorepo_signals))
            row.notable_dirs = [
                RepositoryNotableDir(path=d.path, purpose=d.purpose, pattern_id=d.pattern_id)
                for d in layout.notable_dirs
            ]
            row.manifests = [_manifest_row(m) for m in layout.manifests]
            row.frameworks = [
                RepositoryFramework(
                    framework_id=f.id,
                    name=f.name,
                    category=f.category,
                    evidence=f.evidence,
                    path=f.path,
                    position=position,
                )
                for position, f in enumerate(info.frameworks)
            ]
            row.tooling = [
                RepositoryTool(
                    tool_id=t.id,
                    name=t.name,
                    category=t.category,
                    evidence=t.evidence,
                    path=t.path,
                    position=position,
                )
                for position, t in enumerate(info.tooling)
            ]
            session.flush()
            return _info(row)
