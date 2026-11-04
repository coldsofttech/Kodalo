"""Settings hold a plain ``value`` and a ``data_type`` instead of a JSON ``value_json``.

Everything defaults to a string. Existing rows are carried over: a JSON string becomes the string
itself, a number or true/false gets its type, and anything else stays JSON text.

Revision ID: 0008
Revises: 0007

Like the migrations before it, it skips what already exists, so a second run can finish one that
was cut short.
"""

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

DATA_TYPES = ("string", "integer", "boolean", "float", "json")
CHECK = "data_type IN (" + ", ".join(repr(t) for t in DATA_TYPES) + ")"


def _settings() -> sa.Table:
    return sa.Table(
        "settings",
        sa.MetaData(),
        sa.Column("id", sa.String(36)),
        sa.Column("value", sa.Text()),
        sa.Column("data_type", sa.String(16)),
    )


def _typed(raw: str) -> tuple[str, str]:
    """The ``(value, data_type)`` for a stored JSON text."""
    try:
        loaded: Any = json.loads(raw)
    except ValueError:
        return raw, "string"
    if loaded is None:
        return "", "string"
    if isinstance(loaded, str):
        return loaded, "string"
    if isinstance(loaded, bool):
        return str(loaded).lower(), "boolean"
    if isinstance(loaded, int):
        return str(loaded), "integer"
    if isinstance(loaded, float):
        return str(loaded), "float"
    return raw, "json"


def _json(value: str, data_type: str) -> str:
    """The JSON text for a ``value`` of ``data_type``."""
    if data_type == "string":
        return json.dumps(value)
    if data_type == "boolean":
        return json.dumps(value == "true")
    if data_type == "integer":
        return json.dumps(int(value))
    if data_type == "float":
        return json.dumps(float(value))
    return value


def upgrade() -> None:
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("settings")}
    if "data_type" in columns and "value" in columns:
        return
    with op.batch_alter_table("settings") as batch:
        if "value_json" in columns:
            batch.alter_column(
                "value_json",
                new_column_name="value",
                existing_type=sa.Text(),
                existing_nullable=False,
            )
        batch.add_column(
            sa.Column("data_type", sa.String(16), nullable=False, server_default="string")
        )
        batch.create_check_constraint("data_type", CHECK)
    table = _settings()
    for row in connection.execute(sa.select(table.c.id, table.c.value)).all():
        value, data_type = _typed(row.value)
        connection.execute(
            table.update().where(table.c.id == row.id).values(value=value, data_type=data_type)
        )


def downgrade() -> None:
    connection = op.get_bind()
    table = _settings()
    for row in connection.execute(sa.select(table.c.id, table.c.value, table.c.data_type)).all():
        connection.execute(
            table.update().where(table.c.id == row.id).values(value=_json(row.value, row.data_type))
        )
    with op.batch_alter_table("settings") as batch:
        batch.drop_constraint("data_type", type_="check")
        batch.drop_column("data_type")
        batch.alter_column(
            "value", new_column_name="value_json", existing_type=sa.Text(), existing_nullable=False
        )
