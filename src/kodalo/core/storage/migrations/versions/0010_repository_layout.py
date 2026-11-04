"""Notable folders and monorepo detection.

Adds the seed tables (``directory_patterns``, ``monorepo_signals``, ``manifest_files``,
``ignored_directories``), the per repository tables (``repository_notable_dirs``,
``repository_manifests``) and two columns on ``repositories``. Like the migrations before it, this
one skips what already exists, so a second run can finish one that was cut short.

Revision ID: 0010
Revises: 0009
"""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# (purpose, max_depth, names)
_PATTERNS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    ("source", 2, ("src", "lib", "app", "pkg", "cmd", "internal", "crates", "sources", "source")),
    ("tests", 2, ("tests", "test", "spec", "__tests__", "e2e", "cypress", "playwright")),
    ("docs", 2, ("docs", "doc", "documentation", "wiki", "website")),
    ("examples", 2, ("examples", "example", "samples", "demo", "demos")),
    ("scripts", 2, ("scripts", "tools", "bin", "buildsrc", "build-logic", "tasks")),
    (
        "ci",
        1,
        (".github", ".gitlab", ".circleci", ".azure-pipelines", ".devcontainer", ".vscode"),
    ),
    ("infra", 2, ("docker", "deploy", "infra", "terraform", "k8s", "helm", "charts", "ansible")),
    ("workspace", 1, ("apps", "packages", "services", "modules", "libs", "plugins", "extensions")),
    ("assets", 2, ("public", "static", "assets", "web", "client", "frontend")),
    ("platform", 1, ("android", "ios", "macos", "windows", "linux", "electron", "src-tauri")),
    ("data", 2, ("migrations", "db", "schema", "fixtures", "data")),
    ("packaging", 2, ("installer", "packaging")),
)
# (purpose, max_depth, path ending)
_SUFFIX_PATTERNS = (("tests", 3, "src/test"),)

# (ecosystem, project files, lockfiles)
_MANIFESTS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("js", ("package.json",), ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")),
    ("python", ("pyproject.toml", "setup.py", "requirements*.txt", "Pipfile"), ("uv.lock",)),
    ("rust", ("Cargo.toml",), ("Cargo.lock",)),
    ("go", ("go.mod",), ("go.sum",)),
    ("jvm", ("pom.xml", "build.gradle", "build.gradle.kts"), ()),
    ("dotnet", ("*.csproj", "*.fsproj"), ()),
    ("ruby", ("Gemfile",), ("Gemfile.lock",)),
    ("php", ("composer.json",), ("composer.lock",)),
    ("dart", ("pubspec.yaml",), ("pubspec.lock",)),
    ("swift", ("Package.swift",), ()),
    ("elixir", ("mix.exs",), ()),
    ("cpp", ("CMakeLists.txt",), ()),
)

_FILE_SIGNALS = (
    ("js", "pnpm-workspace.yaml"),
    ("js", "lerna.json"),
    ("js", "nx.json"),
    ("js", "turbo.json"),
    ("js", "rush.json"),
    ("go", "go.work"),
    ("jvm", "settings.gradle"),
    ("jvm", "settings.gradle.kts"),
    ("dart", "melos.yaml"),
    ("bazel", "MODULE.bazel"),
    ("bazel", "WORKSPACE"),
    ("buck", ".buckconfig"),
)
_MULTI_ECOSYSTEMS = ("js", "python", "rust", "go", "jvm", "dotnet", "ruby", "php", "dart")

_IGNORED = (
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".idea",
)


def _row() -> list[sa.Column[str]]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def _stamp(values: list[dict[str, object]]) -> list[dict[str, object]]:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    return [{"id": str(uuid.uuid4()), "created_at": now, "updated_at": now, **v} for v in values]


def _create_tables(connection: sa.Connection) -> None:
    inspector = sa.inspect(connection)
    if not inspector.has_table("directory_patterns"):
        op.create_table(
            "directory_patterns",
            *_row(),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("purpose", sa.String(32), nullable=False),
            sa.Column("match_kind", sa.String(16), nullable=False),
            sa.Column("max_depth", sa.Integer(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", "match_kind"),
        )
    if not inspector.has_table("monorepo_signals"):
        op.create_table(
            "monorepo_signals",
            *_row(),
            sa.Column("ecosystem", sa.String(32), nullable=False),
            sa.Column("signal_kind", sa.String(24), nullable=False),
            sa.Column("file_name", sa.String(128), nullable=False),
            sa.Column("min_count", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(256), nullable=False),
            sa.CheckConstraint(
                "signal_kind IN ('file_exists', 'multi_manifest')", name="signal_kind"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("manifest_files"):
        op.create_table(
            "manifest_files",
            *_row(),
            sa.Column("file_name_pattern", sa.String(128), nullable=False),
            sa.Column("ecosystem", sa.String(32), nullable=False),
            sa.Column("is_lockfile", sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("file_name_pattern"),
        )
    if not inspector.has_table("ignored_directories"):
        op.create_table(
            "ignored_directories",
            *_row(),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("reason", sa.String(128), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
    if not inspector.has_table("repository_notable_dirs"):
        op.create_table(
            "repository_notable_dirs",
            *_row(),
            sa.Column("repository_id", sa.String(36), nullable=False),
            sa.Column("path", sa.String(1024), nullable=False),
            sa.Column("purpose", sa.String(32), nullable=False),
            sa.Column("pattern_id", sa.String(36), nullable=True),
            sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["pattern_id"], ["directory_patterns.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", "path"),
        )
    if not inspector.has_table("repository_manifests"):
        op.create_table(
            "repository_manifests",
            *_row(),
            sa.Column("repository_id", sa.String(36), nullable=False),
            sa.Column("path", sa.String(1024), nullable=False),
            sa.Column("ecosystem", sa.String(32), nullable=False),
            sa.Column("is_lockfile", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", "path"),
        )


def _seed(connection: sa.Connection) -> None:
    patterns = sa.Table("directory_patterns", sa.MetaData(), autoload_with=connection)
    signals = sa.Table("monorepo_signals", sa.MetaData(), autoload_with=connection)
    manifests = sa.Table("manifest_files", sa.MetaData(), autoload_with=connection)
    ignored = sa.Table("ignored_directories", sa.MetaData(), autoload_with=connection)

    pattern_rows: list[dict[str, object]] = []
    for purpose, depth, names in _PATTERNS:
        for name in names:
            pattern_rows.append(
                {"name": name, "purpose": purpose, "match_kind": "exact", "max_depth": depth}
            )
    for purpose, depth, name in _SUFFIX_PATTERNS:
        pattern_rows.append(
            {"name": name, "purpose": purpose, "match_kind": "path_suffix", "max_depth": depth}
        )
    for order, row in enumerate(pattern_rows):
        row["sort_order"] = order

    signal_rows: list[dict[str, object]] = [
        {
            "ecosystem": ecosystem,
            "signal_kind": "file_exists",
            "file_name": file_name,
            "min_count": 1,
            "description": f"{file_name} at the top of the repository",
        }
        for ecosystem, file_name in _FILE_SIGNALS
    ]
    signal_rows += [
        {
            "ecosystem": ecosystem,
            "signal_kind": "multi_manifest",
            "file_name": "",
            "min_count": 2,
            "description": f"{ecosystem} projects in two or more folders",
        }
        for ecosystem in _MULTI_ECOSYSTEMS
    ]

    manifest_rows: list[dict[str, object]] = []
    for ecosystem, names, locks in _MANIFESTS:
        manifest_rows += [
            {"file_name_pattern": n, "ecosystem": ecosystem, "is_lockfile": False} for n in names
        ]
        manifest_rows += [
            {"file_name_pattern": n, "ecosystem": ecosystem, "is_lockfile": True} for n in locks
        ]

    ignored_rows: list[dict[str, object]] = [{"name": n, "reason": "never read"} for n in _IGNORED]
    for table, rows in (
        (patterns, pattern_rows),
        (signals, signal_rows),
        (manifests, manifest_rows),
        (ignored, ignored_rows),
    ):
        if not connection.execute(sa.select(sa.func.count()).select_from(table)).scalar():
            connection.execute(sa.insert(table), _stamp(rows))


def upgrade() -> None:
    connection = op.get_bind()
    _create_tables(connection)
    _seed(connection)
    columns = {column["name"] for column in sa.inspect(connection).get_columns("repositories")}
    if "is_monorepo" not in columns:
        op.add_column(
            "repositories",
            sa.Column("is_monorepo", sa.Boolean(), nullable=False, server_default="0"),
        )
    if "monorepo_signals_json" not in columns:
        op.add_column(
            "repositories",
            sa.Column("monorepo_signals_json", sa.Text(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    op.drop_column("repositories", "monorepo_signals_json")
    op.drop_column("repositories", "is_monorepo")
    for name in (
        "repository_manifests",
        "repository_notable_dirs",
        "ignored_directories",
        "manifest_files",
        "monorepo_signals",
        "directory_patterns",
    ):
        op.drop_table(name)
