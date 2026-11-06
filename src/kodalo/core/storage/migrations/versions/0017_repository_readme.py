"""README analysis: purpose, documents read, installation, capabilities and use cases.

Adds ``repository_readmes``, ``repository_documents``, ``repository_installs``,
``repository_capabilities`` and ``repository_use_cases``. Like the migrations before it, this one
skips what already exists.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

_TABLES = (
    "repository_readmes",
    "repository_documents",
    "repository_installs",
    "repository_capabilities",
    "repository_use_cases",
)


def _text(name: str, size: int, default: str = "") -> sa.Column[str]:
    return sa.Column(name, sa.String(size), nullable=False, server_default=default)


def _evidence(status: str) -> list[sa.Column[str] | sa.Column[int]]:
    return [
        _text("file", 1024),
        _text("quote", 128),
        _text("status", 16, status),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    ]


def _create(name: str, *items: sa.schema.SchemaItem) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        *items,
        sa.PrimaryKeyConstraint("id", name=f"pk_{name}"),
    )


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "repository_readmes" not in existing:
        _create(
            "repository_readmes",
            _text("tagline", 256),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            _text("purpose_file", 1024),
            sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("analyzed_at", sa.String(32)),
            sa.Column("use_cases_at", sa.String(32)),
            sa.UniqueConstraint("repository_id", name="uq_repository_readmes_repository_id"),
        )
    if "repository_documents" not in existing:
        _create(
            "repository_documents",
            sa.Column("path", sa.String(1024), nullable=False),
            sa.Column("status", sa.String(8), nullable=False),
            _text("reason", 128),
            sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint(
                "repository_id", "path", name="uq_repository_documents_repository_id"
            ),
        )
    if "repository_installs" not in existing:
        _create(
            "repository_installs",
            sa.Column("method", sa.String(32), nullable=False),
            _text("command", 512),
            _text("note", 256),
            *_evidence("documented"),
        )
    if "repository_capabilities" not in existing:
        _create(
            "repository_capabilities",
            sa.Column("name", sa.String(128), nullable=False),
            _text("description", 512),
            _text("note", 256),
            *_evidence("documented"),
        )
    if "repository_use_cases" not in existing:
        _create(
            "repository_use_cases",
            sa.Column("title", sa.String(128), nullable=False),
            _text("description", 512),
            *_evidence("inferred"),
        )


def downgrade() -> None:
    for name in reversed(_TABLES):
        op.drop_table(name)
