"""Tables of the local database.

Ids are UUID4 text and timestamps are UTC ISO-8601 text. Every table has ``created_at`` and
``updated_at``; status columns are limited by CHECK constraints. Changing a table here needs a
migration in ``migrations/versions/``; a test fails when the two disagree.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

VERSION_TABLE = "schema_migrations"
ORIGINS = ("repository", "inferred", "user_added")
FEATURE_STATUSES = ("verified", "partially_verified", "documented_only", "planned")
AI_PROVIDERS = ("claude_api", "claude_code", "chatgpt_api", "gemini_api")
AI_MODEL_SOURCES = ("fetched", "manual")
SETTING_SCOPES = ("global", "product")
SETTING_MODES = ("inherit", "override", "own")
SETTING_DATA_TYPES = ("string", "integer", "boolean", "float", "json")
CANVAS_TYPES = ("system", "user")
ENTRY_TYPES = ("file", "dir")
SIGNAL_KINDS = ("file_exists", "multi_manifest")
FONT_SOURCES = ("bundled", "system")
FONT_CATEGORIES = ("sans", "serif", "display", "mono")
FONT_COLUMNS = ("body", "body_alt", "heading", "heading_alt", "mono", "mono_alt")
LAYOUT_ALIGNS = ("left", "center")
LAYOUT_DENSITIES = ("compact", "regular", "spacious")
LOGO_POSITIONS = (
    "top_left",
    "top_center",
    "top_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
)
LOGO_SHOW_ON = ("all", "first", "last")

_NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def new_id() -> str:
    """Return a new stable identifier."""
    return str(uuid.uuid4())


def utc_now() -> str:
    """Return the current time as UTC ISO-8601 text."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def in_values(column: str, values: tuple[str, ...]) -> str:
    """Return a CHECK expression limiting ``column`` to ``values``."""
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING)


class _Row:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[str] = mapped_column(String(32), default=utc_now)
    updated_at: Mapped[str] = mapped_column(String(32), default=utc_now, onupdate=utc_now)


class Setting(_Row, Base):
    """One setting: ``value`` is text read as ``data_type``. Global rows have no ``owner_id``."""

    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("scope", "owner_id", "group_name", "key"),
        CheckConstraint(in_values("scope", SETTING_SCOPES), name="scope"),
        CheckConstraint(in_values("mode", SETTING_MODES), name="mode"),
        CheckConstraint(in_values("data_type", SETTING_DATA_TYPES), name="data_type"),
    )

    scope: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[str] = mapped_column(String(36), default="")
    group_name: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(16), default="inherit")
    value: Mapped[str] = mapped_column(Text, default="")
    data_type: Mapped[str] = mapped_column(String(16), default="string", server_default="string")


class BrandProfile(_Row, Base):
    """A named brand. Its colors, fonts, layout and logo live in the ``brand_*`` tables, one row
    each; at most one profile is the default."""

    __tablename__ = "brand_profiles"
    __table_args__ = (
        Index(
            "uq_brand_profiles_default",
            "is_default",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(128), unique=True)
    is_default: Mapped[bool] = mapped_column(default=False)

    colors: Mapped["BrandColorsRow | None"] = relationship(
        cascade="all, delete-orphan", single_parent=True, lazy="selectin"
    )
    fonts: Mapped["BrandFontsRow | None"] = relationship(
        cascade="all, delete-orphan", single_parent=True, lazy="selectin"
    )
    layout_id: Mapped[str | None] = mapped_column(ForeignKey("layouts.id"))
    layout: Mapped["LayoutRow | None"] = relationship(lazy="joined")
    logo: Mapped["BrandLogoRow | None"] = relationship(
        cascade="all, delete-orphan", single_parent=True, lazy="selectin"
    )


class Canvas(_Row, Base):
    """A named slide size. ``system`` rows are built in; ``user`` rows are made by the user."""

    __tablename__ = "canvases"
    __table_args__ = (
        CheckConstraint(in_values("type", CANVAS_TYPES), name="type"),
        Index("uq_canvases_name", "name", unique=True),
    )

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(64))
    width: Mapped[int]
    height: Mapped[int]
    type: Mapped[str] = mapped_column(String(8), default="user")


class PaletteRow(_Row, Base):
    """A named set of the eight brand colors. ``system`` rows are built in; ``user`` rows are the
    user's own. A brand copies a palette's colors, so palettes are never "in use"."""

    __tablename__ = "palettes"
    __table_args__ = (
        CheckConstraint(in_values("type", CANVAS_TYPES), name="type"),
        Index("uq_palettes_name", "name", unique=True),
    )

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(8), default="user")
    background_light: Mapped[str] = mapped_column(String(7))
    background_dark: Mapped[str] = mapped_column(String(7))
    background_alt_light: Mapped[str] = mapped_column(String(7))
    background_alt_dark: Mapped[str] = mapped_column(String(7))
    primary_light: Mapped[str] = mapped_column(String(7))
    primary_dark: Mapped[str] = mapped_column(String(7))
    primary_alt_light: Mapped[str] = mapped_column(String(7))
    primary_alt_dark: Mapped[str] = mapped_column(String(7))
    secondary_light: Mapped[str] = mapped_column(String(7))
    secondary_dark: Mapped[str] = mapped_column(String(7))
    secondary_alt_light: Mapped[str] = mapped_column(String(7))
    secondary_alt_dark: Mapped[str] = mapped_column(String(7))
    text_light: Mapped[str] = mapped_column(String(7))
    text_dark: Mapped[str] = mapped_column(String(7))
    text_alt_light: Mapped[str] = mapped_column(String(7))
    text_alt_dark: Mapped[str] = mapped_column(String(7))


class _BrandPart:
    """Columns every ``brand_*`` table shares. The profile id is the primary key."""

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    created_at: Mapped[str] = mapped_column(String(32), default=utc_now)
    updated_at: Mapped[str] = mapped_column(String(32), default=utc_now, onupdate=utc_now)


class BrandColorsRow(_BrandPart, Base):
    """The eight brand colors, each with a light and a dark value (``#rrggbb``)."""

    __tablename__ = "brand_colors"

    profile_id: Mapped[str] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    background_light: Mapped[str] = mapped_column(String(7))
    background_dark: Mapped[str] = mapped_column(String(7))
    background_alt_light: Mapped[str] = mapped_column(String(7))
    background_alt_dark: Mapped[str] = mapped_column(String(7))
    primary_light: Mapped[str] = mapped_column(String(7))
    primary_dark: Mapped[str] = mapped_column(String(7))
    primary_alt_light: Mapped[str] = mapped_column(String(7))
    primary_alt_dark: Mapped[str] = mapped_column(String(7))
    secondary_light: Mapped[str] = mapped_column(String(7))
    secondary_dark: Mapped[str] = mapped_column(String(7))
    secondary_alt_light: Mapped[str] = mapped_column(String(7))
    secondary_alt_dark: Mapped[str] = mapped_column(String(7))
    text_light: Mapped[str] = mapped_column(String(7))
    text_dark: Mapped[str] = mapped_column(String(7))
    text_alt_light: Mapped[str] = mapped_column(String(7))
    text_alt_dark: Mapped[str] = mapped_column(String(7))


class FontRow(_Row, Base):
    """A font brands can use. Bundled fonts are seeded; installed ones are added when seen."""

    __tablename__ = "fonts"
    __table_args__ = (
        CheckConstraint(in_values("category", FONT_CATEGORIES), name="category"),
        CheckConstraint(in_values("source", FONT_SOURCES), name="source"),
        Index("uq_fonts_family", "family", unique=True),
    )

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    family: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(8), default="sans")
    source: Mapped[str] = mapped_column(String(8), default="bundled")


class LayoutRow(_Row, Base):
    """A named slide layout shared by brands. ``system`` rows are built in."""

    __tablename__ = "layouts"
    __table_args__ = (
        CheckConstraint(in_values("type", CANVAS_TYPES), name="type"),
        CheckConstraint(in_values("align", LAYOUT_ALIGNS), name="align"),
        CheckConstraint(in_values("density", LAYOUT_DENSITIES), name="density"),
        Index("uq_layouts_name", "name", unique=True),
    )

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(8), default="user")
    canvas_id: Mapped[str] = mapped_column(ForeignKey("canvases.id"))
    align: Mapped[str] = mapped_column(String(8), default="left")
    corner_radius: Mapped[int] = mapped_column(default=24)
    density: Mapped[str] = mapped_column(String(8), default="regular")
    footer_text: Mapped[str] = mapped_column(String(120), default="")
    margin_bottom: Mapped[int] = mapped_column(default=96)
    margin_side: Mapped[int] = mapped_column(default=80)
    margin_top: Mapped[int] = mapped_column(default=96)
    slide_numbers: Mapped[bool] = mapped_column(default=True)
    slides_count: Mapped[int] = mapped_column(default=6, server_default="6")

    canvas: Mapped[Canvas] = relationship(lazy="joined")


class BrandFontsRow(_BrandPart, Base):
    """The six brand fonts, each a reference to a row of the font catalogue."""

    __tablename__ = "brand_fonts"

    profile_id: Mapped[str] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    body_id: Mapped[str] = mapped_column(ForeignKey("fonts.id"))
    body_alt_id: Mapped[str] = mapped_column(ForeignKey("fonts.id"))
    heading_id: Mapped[str] = mapped_column(ForeignKey("fonts.id"))
    heading_alt_id: Mapped[str] = mapped_column(ForeignKey("fonts.id"))
    mono_id: Mapped[str] = mapped_column(ForeignKey("fonts.id"))
    mono_alt_id: Mapped[str] = mapped_column(ForeignKey("fonts.id"))

    body: Mapped[FontRow] = relationship(foreign_keys=[body_id], lazy="joined")
    body_alt: Mapped[FontRow] = relationship(foreign_keys=[body_alt_id], lazy="joined")
    heading: Mapped[FontRow] = relationship(foreign_keys=[heading_id], lazy="joined")
    heading_alt: Mapped[FontRow] = relationship(foreign_keys=[heading_alt_id], lazy="joined")
    mono: Mapped[FontRow] = relationship(foreign_keys=[mono_id], lazy="joined")
    mono_alt: Mapped[FontRow] = relationship(foreign_keys=[mono_alt_id], lazy="joined")


class BrandLogoRow(_BrandPart, Base):
    """Logo file names refer to the logo store, never to paths."""

    __tablename__ = "brand_logos"
    __table_args__ = (
        CheckConstraint(in_values("position", LOGO_POSITIONS), name="position"),
        CheckConstraint(in_values("show_on", LOGO_SHOW_ON), name="show_on"),
    )

    profile_id: Mapped[str] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    file: Mapped[str | None] = mapped_column(String(64))
    dark_file: Mapped[str | None] = mapped_column(String(64))
    padding: Mapped[int] = mapped_column(default=48)
    position: Mapped[str] = mapped_column(String(16), default="top_left")
    show_on: Mapped[str] = mapped_column(String(8), default="all")
    size_percent: Mapped[int] = mapped_column(default=14)


class AiConnectionRow(_Row, Base):
    """A connection to an AI provider, one row per provider. Never holds a secret: ``secret_ref``
    names the key in the system keychain. At most one connection is the default."""

    __tablename__ = "ai_connections"
    __table_args__ = (
        CheckConstraint(in_values("provider", AI_PROVIDERS), name="provider"),
        Index("uq_ai_connections_provider", "provider", unique=True),
        Index(
            "uq_ai_connections_default",
            "is_default",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )

    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    provider: Mapped[str] = mapped_column(String(16))
    enabled: Mapped[bool] = mapped_column(default=True)
    is_default: Mapped[bool] = mapped_column(default=False)
    base_url: Mapped[str] = mapped_column(String(512), default="", server_default="")
    secret_ref: Mapped[str | None] = mapped_column(String(128))
    key_hint: Mapped[str] = mapped_column(String(8), default="", server_default="")
    last_status: Mapped[str] = mapped_column(String(8), default="", server_default="")
    last_detail: Mapped[str] = mapped_column(String(256), default="", server_default="")
    last_checked_at: Mapped[str | None] = mapped_column(String(32))

    models: Mapped[list["AiModelRow"]] = relationship(
        back_populates="connection",
        cascade="all, delete-orphan",
        order_by="AiModelRow.name",
        lazy="selectin",
    )


class AiModelRow(_Row, Base):
    """A model of an AI connection, with its generation defaults. ``fetched`` rows come from the
    provider; ``manual`` rows are typed in and survive a refresh. At most one model per connection
    is the default; empty parameters mean "use the provider's own default"."""

    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint("connection_id", "name"),
        CheckConstraint(in_values("source", AI_MODEL_SOURCES), name="source"),
        Index(
            "uq_ai_models_default",
            "connection_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
    )

    connection_id: Mapped[str] = mapped_column(ForeignKey("ai_connections.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(8), default="manual")
    is_default: Mapped[bool] = mapped_column(default=False)
    max_tokens: Mapped[int | None]
    temperature: Mapped[float | None]
    timeout_s: Mapped[int | None]

    connection: Mapped[AiConnectionRow] = relationship(back_populates="models")


class Repository(_Row, Base):
    __tablename__ = "repositories"

    url: Mapped[str] = mapped_column(String(512), unique=True)
    owner: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    default_branch: Mapped[str | None] = mapped_column(String(128))
    is_private: Mapped[bool] = mapped_column(default=False)
    last_scanned_at: Mapped[str | None] = mapped_column(String(32))
    homepage: Mapped[str] = mapped_column(String(512), default="", server_default="")
    license: Mapped[str | None] = mapped_column(String(128))
    is_fork: Mapped[bool] = mapped_column(default=False, server_default="0")
    is_archived: Mapped[bool] = mapped_column(default=False, server_default="0")
    last_pushed_at: Mapped[str | None] = mapped_column(String(40))
    access_method: Mapped[str] = mapped_column(String(16), default="", server_default="")
    tree_truncated: Mapped[bool] = mapped_column(default=False, server_default="0")
    file_count: Mapped[int] = mapped_column(default=0, server_default="0")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    local_path: Mapped[str] = mapped_column(String(1024), default="", server_default="")
    is_monorepo: Mapped[bool] = mapped_column(default=False, server_default="0")
    monorepo_signals_json: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")

    tools: Mapped[list["Tool"]] = relationship(back_populates="repository")
    languages: Mapped[list["RepositoryLanguage"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="RepositoryLanguage.bytes.desc()",
    )
    topics: Mapped[list["RepositoryTopic"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="RepositoryTopic.position",
    )
    entries: Mapped[list["RepositoryEntry"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="RepositoryEntry.position",
    )
    notable_dirs: Mapped[list["RepositoryNotableDir"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="RepositoryNotableDir.path",
    )
    manifests: Mapped[list["RepositoryManifest"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="RepositoryManifest.path",
    )


class RepositoryLanguage(_Row, Base):
    """One language of a repository, with its size in bytes and its share of all bytes."""

    __tablename__ = "repository_languages"
    __table_args__ = (UniqueConstraint("repository_id", "name"),)

    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(default=0)
    percent: Mapped[float] = mapped_column(default=0.0)

    repository: Mapped["Repository"] = relationship(back_populates="languages")


class RepositoryTopic(_Row, Base):
    """One topic of a repository. ``position`` keeps them in the order they were read."""

    __tablename__ = "repository_topics"
    __table_args__ = (UniqueConstraint("repository_id", "name"),)

    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(128))
    position: Mapped[int] = mapped_column(default=0)

    repository: Mapped["Repository"] = relationship(back_populates="topics")


class RepositoryEntry(_Row, Base):
    """One file or folder at the top level of a repository, in the order it was read."""

    __tablename__ = "repository_entries"
    __table_args__ = (
        UniqueConstraint("repository_id", "path"),
        CheckConstraint(in_values("type", ENTRY_TYPES), name="type"),
    )

    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String(1024))
    type: Mapped[Literal["file", "dir"]] = mapped_column(String(8))
    position: Mapped[int] = mapped_column(default=0)

    repository: Mapped["Repository"] = relationship(back_populates="entries")


class RepositoryNotableDir(_Row, Base):
    """A folder with a well-known name, such as ``tests``, and what it is for."""

    __tablename__ = "repository_notable_dirs"
    __table_args__ = (UniqueConstraint("repository_id", "path"),)

    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String(1024))
    purpose: Mapped[str] = mapped_column(String(32))
    pattern_id: Mapped[str | None] = mapped_column(
        ForeignKey("directory_patterns.id", ondelete="SET NULL")
    )

    repository: Mapped["Repository"] = relationship(back_populates="notable_dirs")


class RepositoryManifest(_Row, Base):
    """A project file, such as ``package.json``, found in a repository."""

    __tablename__ = "repository_manifests"
    __table_args__ = (UniqueConstraint("repository_id", "path"),)

    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String(1024))
    ecosystem: Mapped[str] = mapped_column(String(32))
    is_lockfile: Mapped[bool] = mapped_column(default=False)
    package_name: Mapped[str | None] = mapped_column(String(256))
    version: Mapped[str | None] = mapped_column(String(256))

    repository: Mapped["Repository"] = relationship(back_populates="manifests")
    dependencies: Mapped[list["RepositoryDependency"]] = relationship(
        back_populates="manifest",
        cascade="all, delete-orphan",
        order_by="RepositoryDependency.position",
    )


class RepositoryDependency(_Row, Base):
    """One package a project file depends on. ``is_dev`` marks test and tooling packages."""

    __tablename__ = "repository_dependencies"
    __table_args__ = (UniqueConstraint("manifest_id", "name", "is_dev"),)

    manifest_id: Mapped[str] = mapped_column(
        ForeignKey("repository_manifests.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(256))
    is_dev: Mapped[bool] = mapped_column(default=False)
    position: Mapped[int] = mapped_column(default=0)

    manifest: Mapped["RepositoryManifest"] = relationship(back_populates="dependencies")


class DirectoryPattern(_Row, Base):
    """Seed data: a folder name and what it is for. Read only while the app runs."""

    __tablename__ = "directory_patterns"
    __table_args__ = (UniqueConstraint("name", "match_kind"),)

    name: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[str] = mapped_column(String(32))
    match_kind: Mapped[str] = mapped_column(String(16), default="exact")
    max_depth: Mapped[int] = mapped_column(default=2)
    sort_order: Mapped[int] = mapped_column(default=0)


class MonorepoSignal(_Row, Base):
    """Seed data: a sign that a repository holds several projects."""

    __tablename__ = "monorepo_signals"
    __table_args__ = (CheckConstraint(in_values("signal_kind", SIGNAL_KINDS), name="signal_kind"),)

    ecosystem: Mapped[str] = mapped_column(String(32))
    signal_kind: Mapped[str] = mapped_column(String(24))
    file_name: Mapped[str] = mapped_column(String(128), default="")
    min_count: Mapped[int] = mapped_column(default=1)
    description: Mapped[str] = mapped_column(String(256), default="")


class IgnoredDirectory(_Row, Base):
    """Seed data: a folder that is never read, such as ``node_modules``."""

    __tablename__ = "ignored_directories"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    reason: Mapped[str] = mapped_column(String(128), default="")


class Tool(_Row, Base):
    """A product or tool. ``repository_id`` is empty for a product entered by hand."""

    __tablename__ = "tools"
    __table_args__ = (CheckConstraint(in_values("origin", ORIGINS), name="origin"),)

    repository_id: Mapped[str | None] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    origin: Mapped[str] = mapped_column(String(16), default="user_added")

    repository: Mapped[Repository | None] = relationship(back_populates="tools")
    features: Mapped[list["Feature"]] = relationship(back_populates="tool")


class Feature(_Row, Base):
    __tablename__ = "features"
    __table_args__ = (
        CheckConstraint(in_values("origin", ORIGINS), name="origin"),
        CheckConstraint(in_values("status", FEATURE_STATUSES), name="status"),
    )

    tool_id: Mapped[str] = mapped_column(ForeignKey("tools.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    problem: Mapped[str] = mapped_column(Text, default="")
    benefit: Mapped[str] = mapped_column(Text, default="")
    origin: Mapped[str] = mapped_column(String(16), default="user_added")
    status: Mapped[str] = mapped_column(String(24), default="documented_only")
    user_edited: Mapped[bool] = mapped_column(default=False)

    tool: Mapped[Tool] = relationship(back_populates="features")
    evidence: Mapped[list["FeatureEvidence"]] = relationship(back_populates="feature")


class FeatureEvidence(_Row, Base):
    __tablename__ = "feature_evidence"

    feature_id: Mapped[str] = mapped_column(ForeignKey("features.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String(1024))
    excerpt: Mapped[str] = mapped_column(Text, default="")

    feature: Mapped[Feature] = relationship(back_populates="evidence")
