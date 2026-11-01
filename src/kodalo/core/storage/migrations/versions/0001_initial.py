"""Initial tables: settings, brand profiles, provider settings, repositories, tools and features.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ORIGIN = "origin IN ('repository', 'inferred', 'user_added')"


def _row() -> list[sa.Column[str]]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "settings",
        *_row(),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("group_name", sa.String(64), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.CheckConstraint("scope IN ('global', 'product')", name="scope"),
        sa.CheckConstraint("mode IN ('inherit', 'override', 'own')", name="mode"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "owner_id", "group_name", "key"),
    )
    op.create_table(
        "brand_profiles",
        *_row(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("data_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "provider_settings",
        *_row(),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("endpoint", sa.String(512), nullable=True),
        sa.Column("models_json", sa.Text(), nullable=False),
        sa.Column("credential_ref", sa.String(256), nullable=True),
        sa.Column("last_test_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "provider_type IN ('claude_code_cli', 'gemini_api', 'openai_compatible')",
            name="provider_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("display_name"),
    )
    op.create_table(
        "repositories",
        *_row(),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("default_branch", sa.String(128), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("last_scanned_at", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_table(
        "tools",
        *_row(),
        sa.Column("repository_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.CheckConstraint(ORIGIN, name="origin"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "features",
        *_row(),
        sa.Column("tool_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("benefit", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("user_edited", sa.Boolean(), nullable=False),
        sa.CheckConstraint(ORIGIN, name="origin"),
        sa.CheckConstraint(
            "status IN ('verified', 'partially_verified', 'documented_only', 'planned')",
            name="status",
        ),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "feature_evidence",
        *_row(),
        sa.Column("feature_id", sa.String(), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
