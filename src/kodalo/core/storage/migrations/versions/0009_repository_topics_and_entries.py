"""Topics and top-level entries move out of JSON columns into their own tables.

``repository_topics`` and ``repository_entries`` hold one row each, in the order they were read.
Existing repositories keep their topics and entries. Like the migrations before it, this one skips
what already exists, so a second run can finish one that was cut short.

Revision ID: 0009
Revises: 0008
"""

import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _row() -> list[sa.Column[str]]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _create_tables(connection: sa.Connection) -> None:
    inspector = sa.inspect(connection)
    if not inspector.has_table("repository_topics"):
        op.create_table(
            "repository_topics",
            *_row(),
            sa.Column("repository_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", "name"),
        )
    if not inspector.has_table("repository_entries"):
        op.create_table(
            "repository_entries",
            *_row(),
            sa.Column("repository_id", sa.String(36), nullable=False),
            sa.Column("path", sa.String(1024), nullable=False),
            sa.Column("type", sa.String(8), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.CheckConstraint("type IN ('file', 'dir')", name="type"),
            sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", "path"),
        )


def _copy_rows(connection: sa.Connection, columns: set[str]) -> None:
    repositories = sa.Table("repositories", sa.MetaData(), autoload_with=connection)
    topics = sa.Table("repository_topics", sa.MetaData(), autoload_with=connection)
    entries = sa.Table("repository_entries", sa.MetaData(), autoload_with=connection)
    now = _now()
    for row in connection.execute(sa.select(repositories)).mappings().all():
        if "topics_json" in columns:
            names = dict.fromkeys(json.loads(row["topics_json"] or "[]"))
            connection.execute(
                sa.insert(topics).prefix_with("OR IGNORE"),
                [
                    {
                        "id": str(uuid.uuid4()),
                        "created_at": now,
                        "updated_at": now,
                        "repository_id": row["id"],
                        "name": name,
                        "position": position,
                    }
                    for position, name in enumerate(names)
                ],
            )
        if "structure_json" in columns:
            found = {e["path"]: e["type"] for e in json.loads(row["structure_json"] or "[]")}
            connection.execute(
                sa.insert(entries).prefix_with("OR IGNORE"),
                [
                    {
                        "id": str(uuid.uuid4()),
                        "created_at": now,
                        "updated_at": now,
                        "repository_id": row["id"],
                        "path": path,
                        "type": kind,
                        "position": position,
                    }
                    for position, (path, kind) in enumerate(found.items())
                ],
            )


def upgrade() -> None:
    connection = op.get_bind()
    _create_tables(connection)
    columns = {column["name"] for column in sa.inspect(connection).get_columns("repositories")}
    old = columns & {"topics_json", "structure_json"}
    if not old:
        return
    _copy_rows(connection, columns)
    # Not a batch: rebuilding ``repositories`` would cascade-delete the rows just copied.
    for name in sorted(old):
        op.drop_column("repositories", name)


def downgrade() -> None:
    connection = op.get_bind()
    op.add_column(
        "repositories", sa.Column("topics_json", sa.Text(), nullable=False, server_default="[]")
    )
    op.add_column(
        "repositories", sa.Column("structure_json", sa.Text(), nullable=False, server_default="[]")
    )
    repositories = sa.Table("repositories", sa.MetaData(), autoload_with=connection)
    topics = sa.Table("repository_topics", sa.MetaData(), autoload_with=connection)
    entries = sa.Table("repository_entries", sa.MetaData(), autoload_with=connection)
    for repository_id in connection.execute(sa.select(repositories.c.id)).scalars().all():
        names = (
            connection.execute(
                sa.select(topics.c.name)
                .where(topics.c.repository_id == repository_id)
                .order_by(topics.c.position)
            )
            .scalars()
            .all()
        )
        found = connection.execute(
            sa.select(entries.c.path, entries.c.type)
            .where(entries.c.repository_id == repository_id)
            .order_by(entries.c.position)
        ).all()
        connection.execute(
            repositories.update()
            .where(repositories.c.id == repository_id)
            .values(
                topics_json=json.dumps(list(names)),
                structure_json=json.dumps([{"path": p, "type": t} for p, t in found]),
            )
        )
    op.drop_table("repository_entries")
    op.drop_table("repository_topics")
