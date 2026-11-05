"""History of calls to AI providers.

Adds the ``ai_calls`` table. Like the migrations before it, this one skips what already exists.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("ai_calls"):
        return
    op.create_table(
        "ai_calls",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("purpose", sa.String(24), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("error", sa.String(256), server_default="", nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('ok', 'failed')", name="status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_calls_created_at", "ai_calls", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_calls_created_at", table_name="ai_calls")
    op.drop_table("ai_calls")
