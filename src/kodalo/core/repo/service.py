"""Read repositories the way the GitHub setting says, and keep what was read in the database."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.github import GitHubSettings
from kodalo.core.repo.errors import RepoDetailsError, RepoNotFoundError
from kodalo.core.repo.github_reader import Fetch, gh_fetch, read_github, web_fetch
from kodalo.core.repo.local_reader import read_local
from kodalo.core.repo.models import Entry, Language, LocalDetails, RepoInfo
from kodalo.core.storage import Database
from kodalo.core.storage.models import Repository, RepositoryLanguage, utc_now
from kodalo.core.studio import Source


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
        topics=tuple(json.loads(row.topics_json)),
        is_private=row.is_private,
        is_fork=row.is_fork,
        is_archived=row.is_archived,
        last_pushed_at=row.last_pushed_at,
        languages=tuple(Language(lang.name, lang.bytes, lang.percent) for lang in row.languages),
        top_level=tuple(Entry(e["path"], e["type"]) for e in json.loads(row.structure_json)),
        file_count=row.file_count,
        access_method=row.access_method,
        tree_truncated=row.tree_truncated,
        warnings=tuple(json.loads(row.warnings_json)),
        local_path=row.local_path,
        last_scanned_at=row.last_scanned_at,
    )


class RepoService:
    """Repositories kept in the local database."""

    def __init__(self, database: Database, *, gh: Fetch = gh_fetch, web: Fetch = web_fetch) -> None:
        self._database = database
        self._gh = gh
        self._web = web

    # Reading from the database

    def list_repos(self) -> list[RepoInfo]:
        """Return every stored repository, sorted by owner and name."""
        with self._database.session() as session:
            rows = session.scalars(select(Repository)).all()
            return sorted((_info(r) for r in rows), key=lambda i: (i.owner.lower(), i.name.lower()))

    def get(self, repo_id: str) -> RepoInfo:
        with self._database.session() as session:
            row = session.get(Repository, repo_id)
            if row is None:
                raise RepoNotFoundError("That repository is not stored.")
            return _info(row)

    def stored(self, source: Source) -> RepoInfo | None:
        """Return the stored repository for ``source``, if it was read before."""
        with self._database.session() as session:
            row = self._find(session, source)
            return _info(row) if row is not None else None

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
        return self._save(info)

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

    def _save(self, info: RepoInfo) -> RepoInfo:
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
            row.topics_json = json.dumps(list(info.topics))
            row.is_private = info.is_private
            row.is_fork = info.is_fork
            row.is_archived = info.is_archived
            row.last_pushed_at = info.last_pushed_at
            row.access_method = info.access_method
            row.tree_truncated = info.tree_truncated
            row.file_count = info.file_count
            row.structure_json = json.dumps(
                [{"path": e.path, "type": e.type} for e in info.top_level]
            )
            row.warnings_json = json.dumps(list(info.warnings))
            row.local_path = info.local_path
            row.last_scanned_at = utc_now()
            row.languages.clear()
            session.flush()  # remove the old rows before adding rows with the same names
            row.languages = [
                RepositoryLanguage(name=lang.name, bytes=lang.bytes, percent=lang.percent)
                for lang in info.languages
            ]
            session.flush()
            return _info(row)
