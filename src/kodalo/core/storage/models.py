"""Tables of the local database.

Ids are UUID4 text and timestamps are UTC ISO-8601 text. Every table has ``created_at`` and
``updated_at``; status columns are limited by CHECK constraints. Changing a table here needs a
migration in ``migrations/versions/``; a test fails when the two disagree.
"""

import uuid
from datetime import UTC, datetime

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
PROVIDER_TYPES = ("claude_code_cli", "gemini_api", "openai_compatible")
SETTING_SCOPES = ("global", "product")
SETTING_MODES = ("inherit", "override", "own")

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
    """One setting value. Global rows use an empty ``owner_id``."""

    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("scope", "owner_id", "group_name", "key"),
        CheckConstraint(in_values("scope", SETTING_SCOPES), name="scope"),
        CheckConstraint(in_values("mode", SETTING_MODES), name="mode"),
    )

    scope: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[str] = mapped_column(String(36), default="")
    group_name: Mapped[str] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(16), default="inherit")
    value_json: Mapped[str] = mapped_column(Text, default="null")


class BrandProfile(_Row, Base):
    """A named brand. ``data_json`` holds the colors, fonts, logo and layout; at most one row is the
    default."""

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
    data_json: Mapped[str] = mapped_column(Text, default="{}")


class ProviderSetting(_Row, Base):
    """A connection to an AI provider. Non-secret values only; ``credential_ref`` names a secret."""

    __tablename__ = "provider_settings"
    __table_args__ = (
        CheckConstraint(in_values("provider_type", PROVIDER_TYPES), name="provider_type"),
    )

    provider_type: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(128), unique=True)
    endpoint: Mapped[str | None] = mapped_column(String(512))
    models_json: Mapped[str] = mapped_column(Text, default="[]")
    credential_ref: Mapped[str | None] = mapped_column(String(256))
    last_test_json: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")


class Repository(_Row, Base):
    __tablename__ = "repositories"

    url: Mapped[str] = mapped_column(String(512), unique=True)
    owner: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    default_branch: Mapped[str | None] = mapped_column(String(128))
    is_private: Mapped[bool] = mapped_column(default=False)
    last_scanned_at: Mapped[str | None] = mapped_column(String(32))

    tools: Mapped[list["Tool"]] = relationship(back_populates="repository")


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
