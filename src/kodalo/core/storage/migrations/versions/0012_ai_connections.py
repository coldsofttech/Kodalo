"""AI connections and their models.

Replaces the unused ``provider_settings`` table with ``ai_connections`` (one row per provider,
holding no secret) and ``ai_models`` (the models of a connection, with generation defaults).

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

PROVIDERS = "provider IN ('claude_api', 'claude_code', 'chatgpt_api', 'gemini_api')"
SOURCES = "source IN ('fetched', 'manual')"


def _row() -> list[sa.Column[str]]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("provider_settings"):
        op.drop_table("provider_settings")
    if not inspector.has_table("ai_connections"):
        op.create_table(
            "ai_connections",
            *_row(),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("provider", sa.String(16), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False),
            sa.Column("base_url", sa.String(512), nullable=False, server_default=""),
            sa.Column("secret_ref", sa.String(128), nullable=True),
            sa.Column("key_hint", sa.String(8), nullable=False, server_default=""),
            sa.Column("last_status", sa.String(8), nullable=False, server_default=""),
            sa.Column("last_detail", sa.String(256), nullable=False, server_default=""),
            sa.Column("last_checked_at", sa.String(32), nullable=True),
            sa.CheckConstraint(PROVIDERS, name="provider"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("uq_ai_connections_provider", "ai_connections", ["provider"], unique=True)
        op.create_index(
            "uq_ai_connections_default",
            "ai_connections",
            ["is_default"],
            unique=True,
            sqlite_where=sa.text("is_default = 1"),
        )
    if not inspector.has_table("ai_models"):
        op.create_table(
            "ai_models",
            *_row(),
            sa.Column("connection_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("source", sa.String(8), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False),
            sa.Column("max_tokens", sa.Integer(), nullable=True),
            sa.Column("temperature", sa.Double(), nullable=True),
            sa.Column("timeout_s", sa.Integer(), nullable=True),
            sa.CheckConstraint(SOURCES, name="source"),
            sa.ForeignKeyConstraint(["connection_id"], ["ai_connections.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("connection_id", "name"),
        )
        op.create_index(
            "uq_ai_models_default",
            "ai_models",
            ["connection_id"],
            unique=True,
            sqlite_where=sa.text("is_default = 1"),
        )


def downgrade() -> None:
    op.drop_table("ai_models")
    op.drop_table("ai_connections")
    # Recreated empty: the table was never used.
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
