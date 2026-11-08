"""Initial schema: settings, brands, AI connections, repository analysis, studio and seed data.

Revision ID: 0001
Revises:
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ORIGIN = "origin IN ('repository', 'inferred', 'user_added')"
COLORS = (
    "background",
    "background_alt",
    "primary",
    "primary_alt",
    "secondary",
    "secondary_alt",
    "text",
    "text_alt",
)
FONT_SLOTS = ("body", "body_alt", "heading", "heading_alt", "mono", "mono_alt")
POSITIONS = (
    "IN ('top_left', 'top_center', 'top_right', 'bottom_left', 'bottom_center', 'bottom_right')"
)

PLATFORMS = {"instagram": "Instagram", "custom": "Custom"}
# (platform, name, width, height)
SIZES = (
    ("instagram", "Portrait", 1080, 1350),
    ("instagram", "Square", 1080, 1080),
    ("instagram", "Story", 1080, 1920),
)
# id -> (name, width, height, platform)
CANVASES = {
    "system-instagram_portrait": ("Instagram portrait", 1080, 1350, "instagram"),
    "system-instagram_square": ("Instagram square", 1080, 1080, "instagram"),
    "system-instagram_story": ("Instagram story", 1080, 1920, "instagram"),
    "system-linkedin_landscape": ("LinkedIn landscape", 1200, 627, "custom"),
    "system-x_landscape": ("X landscape", 1600, 900, "custom"),
}
DEFAULT_CANVAS = "system-instagram_portrait"

# name -> (align, density)
SYSTEM_LAYOUTS = {
    "Default": ("left", "regular"),
    "Compact": ("center", "compact"),
    "Spacious": ("left", "spacious"),
}

BUNDLED_FONTS = (
    ("Inter", "sans"),
    ("Poppins", "sans"),
    ("Montserrat", "sans"),
    ("Source Sans 3", "sans"),
    ("Space Grotesk", "display"),
    ("Playfair Display", "serif"),
    ("Lora", "serif"),
    ("JetBrains Mono", "mono"),
    ("Fira Code", "mono"),
    ("IBM Plex Mono", "mono"),
)

# name -> (background, background_alt, primary, primary_alt, secondary, secondary_alt, text,
# text_alt), each as (light, dark).
SYSTEM_PALETTES = {
    "Midnight": (
        ("#ffffff", "#0b1020"),
        ("#f1f5f9", "#151b30"),
        ("#2563eb", "#60a5fa"),
        ("#1d4ed8", "#93c5fd"),
        ("#7c3aed", "#a78bfa"),
        ("#6d28d9", "#c4b5fd"),
        ("#111827", "#f3f4f6"),
        ("#0f172a", "#e5e7eb"),
    ),
    "Paper": (
        ("#faf7f2", "#1c1917"),
        ("#f0e9dd", "#292524"),
        ("#b45309", "#fbbf24"),
        ("#92400e", "#fcd34d"),
        ("#0f766e", "#5eead4"),
        ("#115e59", "#99f6e4"),
        ("#1c1917", "#f5f5f4"),
        ("#292524", "#e7e5e4"),
    ),
    "Graphite": (
        ("#ffffff", "#0a0a0a"),
        ("#f3f4f6", "#171717"),
        ("#111827", "#fafafa"),
        ("#374151", "#e5e5e5"),
        ("#6b7280", "#a3a3a3"),
        ("#4b5563", "#a3a3a3"),
        ("#111827", "#fafafa"),
        ("#111827", "#fafafa"),
    ),
}

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


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row() -> list[sa.Column[str]]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def _version() -> sa.Column[int]:
    return sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1")


def _text(name: str, size: int, default: str = "") -> sa.Column[str]:
    return sa.Column(name, sa.String(size), nullable=False, server_default=default)


def _repository_id() -> sa.Column[str]:
    return sa.Column(
        "repository_id",
        sa.String(36),
        sa.ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )


def _profile() -> list[sa.Column[Any]]:
    return [
        sa.Column("profile_id", sa.String(36), nullable=False),
        _version(),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def _color_columns() -> list[sa.Column[str]]:
    return [
        sa.Column(f"{name}_{tone}", sa.String(7), nullable=False)
        for name in COLORS
        for tone in ("light", "dark")
    ]


def _evidence(status: str) -> list[sa.Column[Any]]:
    return [
        _text("file", 1024),
        _text("quote", 128),
        _text("status", 16, status),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    ]


def _create_settings_and_ai() -> None:
    op.create_table(
        "settings",
        *_row(),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("group_name", sa.String(64), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("data_type", sa.String(16), nullable=False, server_default="string"),
        sa.CheckConstraint("scope IN ('global', 'product')", name="scope"),
        sa.CheckConstraint("mode IN ('inherit', 'override', 'own')", name="mode"),
        sa.CheckConstraint(
            "data_type IN ('string', 'integer', 'boolean', 'float', 'json')", name="data_type"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "owner_id", "group_name", "key"),
    )
    op.create_table(
        "ai_connections",
        *_row(),
        _version(),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("base_url", sa.String(512), nullable=False, server_default=""),
        sa.Column("secret_ref", sa.String(128), nullable=True),
        sa.Column("key_hint", sa.String(8), nullable=False, server_default=""),
        sa.Column("last_status", sa.String(8), nullable=False, server_default=""),
        sa.Column("last_detail", sa.String(256), nullable=False, server_default=""),
        sa.Column("last_checked_at", sa.String(32), nullable=True),
        sa.CheckConstraint(
            "provider IN ('claude_api', 'claude_code', 'chatgpt_api', 'gemini_api')",
            name="provider",
        ),
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
        sa.CheckConstraint("source IN ('fetched', 'manual')", name="source"),
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
    op.create_table(
        "ai_calls",
        *_row(),
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


def _create_brand_tables() -> None:
    op.create_table(
        "social_platforms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
    )
    op.create_index("uq_social_platforms_name", "social_platforms", ["name"], unique=True)
    op.create_table(
        "social_platform_sizes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column(
            "platform_id",
            sa.String(36),
            sa.ForeignKey("social_platforms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.UniqueConstraint("platform_id", "width", "height"),
    )
    op.create_table(
        "canvases",
        *_row(),
        _version(),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.Column("name", sa.String(64), nullable=False, server_default=""),
        sa.Column("platform_id", sa.String(36), sa.ForeignKey("social_platforms.id")),
        sa.CheckConstraint("type IN ('system', 'user')", name="type"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_canvases_name", "canvases", ["name"], unique=True)
    op.create_table(
        "layouts",
        *_row(),
        _version(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.Column("canvas_id", sa.String(36), nullable=False),
        sa.Column("align", sa.String(8), nullable=False),
        sa.Column("corner_radius", sa.Integer(), nullable=False),
        sa.Column("density", sa.String(8), nullable=False),
        sa.Column("footer_text", sa.String(120), nullable=False),
        sa.Column("margin_bottom", sa.Integer(), nullable=False),
        sa.Column("margin_side", sa.Integer(), nullable=False),
        sa.Column("margin_top", sa.Integer(), nullable=False),
        sa.Column("slide_numbers", sa.Boolean(), nullable=False),
        sa.Column("slides_count", sa.Integer(), nullable=False, server_default="6"),
        sa.CheckConstraint("type IN ('system', 'user')", name="type"),
        sa.CheckConstraint("align IN ('left', 'center')", name="align"),
        sa.CheckConstraint("density IN ('compact', 'regular', 'spacious')", name="density"),
        sa.ForeignKeyConstraint(["canvas_id"], ["canvases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_layouts_name", "layouts", ["name"], unique=True)
    op.create_table(
        "fonts",
        *_row(),
        _version(),
        sa.Column("family", sa.String(100), nullable=False),
        sa.Column("category", sa.String(8), nullable=False),
        sa.Column("source", sa.String(8), nullable=False),
        sa.CheckConstraint("category IN ('sans', 'serif', 'display', 'mono')", name="category"),
        sa.CheckConstraint("source IN ('bundled', 'system')", name="source"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_fonts_family", "fonts", ["family"], unique=True)
    op.create_table(
        "palettes",
        *_row(),
        _version(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        *_color_columns(),
        sa.CheckConstraint("type IN ('system', 'user')", name="type"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_palettes_name", "palettes", ["name"], unique=True)
    op.create_table(
        "brand_profiles",
        *_row(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        _version(),
        sa.Column("layout_id", sa.String(36), sa.ForeignKey("layouts.id")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "uq_brand_profiles_default",
        "brand_profiles",
        ["is_default"],
        unique=True,
        sqlite_where=sa.text("is_default = 1"),
    )
    op.create_table(
        "brand_colors",
        *_profile(),
        *_color_columns(),
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )
    op.create_table(
        "brand_fonts",
        *_profile(),
        *[sa.Column(f"{slot}_id", sa.String(36), nullable=False) for slot in FONT_SLOTS],
        *[sa.ForeignKeyConstraint([f"{slot}_id"], ["fonts.id"]) for slot in FONT_SLOTS],
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )
    op.create_table(
        "brand_logos",
        *_profile(),
        sa.Column("file", sa.String(64), nullable=True),
        sa.Column("dark_file", sa.String(64), nullable=True),
        sa.Column("padding", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(16), nullable=False),
        sa.Column("show_on", sa.String(8), nullable=False),
        sa.Column("size_percent", sa.Integer(), nullable=False),
        sa.CheckConstraint(f"position {POSITIONS}", name="position"),
        sa.CheckConstraint("show_on IN ('all', 'first', 'last', 'none')", name="show_on"),
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )


def _create_repository_tables() -> None:
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
        sa.Column("homepage", sa.String(512), nullable=False, server_default=""),
        sa.Column("license", sa.String(128), nullable=True),
        sa.Column("is_fork", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_pushed_at", sa.String(40), nullable=True),
        sa.Column("access_method", sa.String(16), nullable=False, server_default=""),
        sa.Column("tree_truncated", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("local_path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("is_monorepo", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("monorepo_signals_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("documentation_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("skipped_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("icon_candidates_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("icon_path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("icon_ext", sa.String(8), nullable=False, server_default=""),
        sa.Column("icon_checked_at", sa.String(32), nullable=True),
        sa.Column("icon_box_json", sa.String(128), nullable=False, server_default=""),
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
    op.create_table(
        "repository_languages",
        *_row(),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("percent", sa.Double(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "name"),
    )
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
    op.create_table(
        "monorepo_signals",
        *_row(),
        sa.Column("ecosystem", sa.String(32), nullable=False),
        sa.Column("signal_kind", sa.String(24), nullable=False),
        sa.Column("file_name", sa.String(128), nullable=False),
        sa.Column("min_count", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(256), nullable=False),
        sa.CheckConstraint("signal_kind IN ('file_exists', 'multi_manifest')", name="signal_kind"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ignored_directories",
        *_row(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
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
    op.create_table(
        "repository_manifests",
        *_row(),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("ecosystem", sa.String(32), nullable=False),
        sa.Column("is_lockfile", sa.Boolean(), nullable=False),
        sa.Column("package_name", sa.String(256), nullable=True),
        sa.Column("version", sa.String(256), nullable=True),
        sa.Column("evidence", sa.String(128), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "path"),
    )
    op.create_table(
        "repository_dependencies",
        *_row(),
        sa.Column("manifest_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("is_dev", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["repository_manifests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_id", "name", "is_dev"),
    )
    for table, column, extra in (
        ("repository_frameworks", "framework_id", 16),
        ("repository_tooling", "tool_id", 24),
    ):
        op.create_table(
            table,
            *_row(),
            sa.Column("repository_id", sa.String(36), nullable=False),
            sa.Column(column, sa.String(64), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("category", sa.String(extra), nullable=False),
            sa.Column("evidence", sa.String(128), nullable=False),
            sa.Column("path", sa.String(1024), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", column),
        )


def _create_readme_tables() -> None:
    op.create_table(
        "repository_readmes",
        *_row(),
        _repository_id(),
        _text("tagline", 256),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        _text("purpose_file", 1024),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("analyzed_at", sa.String(32)),
        sa.Column("use_cases_at", sa.String(32)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id"),
    )
    op.create_table(
        "repository_documents",
        *_row(),
        _repository_id(),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        _text("reason", 128),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "path"),
    )
    op.create_table(
        "repository_installs",
        *_row(),
        _repository_id(),
        sa.Column("method", sa.String(32), nullable=False),
        _text("command", 512),
        _text("note", 256),
        *_evidence("documented"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "repository_capabilities",
        *_row(),
        _repository_id(),
        sa.Column("name", sa.String(128), nullable=False),
        _text("description", 512),
        _text("note", 256),
        *_evidence("documented"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "repository_use_cases",
        *_row(),
        _repository_id(),
        sa.Column("title", sa.String(128), nullable=False),
        _text("description", 512),
        *_evidence("inferred"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "repository_features",
        *_row(),
        _repository_id(),
        sa.Column("name", sa.String(128), nullable=False),
        _text("description", 512),
        _text("file", 1024),
        _text("quote", 128),
        _text("status", 16, "inferred"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        _text("importance", 16, "supporting"),
        _text("maturity", 16, "unspecified"),
        sa.Column("claims_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("use_cases_json", sa.Text(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_studio_tables() -> None:
    for table, key in (
        ("studio_ideas", "focus_key"),
        ("studio_copy", "copy_key"),
        ("studio_design", "design_key"),
    ):
        op.create_table(
            table,
            *_row(),
            _repository_id(),
            sa.Column(key, sa.String(600), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", key),
        )


def _seed_brand() -> None:
    now = _now()
    stamp = {"created_at": now, "updated_at": now}
    social_platforms = sa.table(
        "social_platforms",
        sa.column("id"),
        sa.column("created_at"),
        sa.column("updated_at"),
        sa.column("name"),
    )
    op.bulk_insert(
        social_platforms, [{"id": key, "name": name, **stamp} for key, name in PLATFORMS.items()]
    )
    sizes = sa.table(
        "social_platform_sizes",
        sa.column("id"),
        sa.column("created_at"),
        sa.column("updated_at"),
        sa.column("platform_id"),
        sa.column("name"),
        sa.column("width"),
        sa.column("height"),
    )
    op.bulk_insert(
        sizes,
        [
            {
                "id": f"{platform}-{name.lower()}",
                "platform_id": platform,
                "name": name,
                "width": width,
                "height": height,
                **stamp,
            }
            for platform, name, width, height in SIZES
        ],
    )
    canvases = sa.table(
        "canvases",
        sa.column("id"),
        sa.column("created_at"),
        sa.column("updated_at"),
        sa.column("name"),
        sa.column("width"),
        sa.column("height"),
        sa.column("type"),
        sa.column("platform_id"),
    )
    op.bulk_insert(
        canvases,
        [
            {
                "id": canvas_id,
                "name": name,
                "width": width,
                "height": height,
                "type": "system",
                "platform_id": platform,
                **stamp,
            }
            for canvas_id, (name, width, height, platform) in CANVASES.items()
        ],
    )
    layouts = sa.table(
        "layouts",
        sa.column("id"),
        sa.column("created_at"),
        sa.column("updated_at"),
        sa.column("name"),
        sa.column("type"),
        sa.column("canvas_id"),
        sa.column("align"),
        sa.column("corner_radius"),
        sa.column("density"),
        sa.column("footer_text"),
        sa.column("margin_bottom"),
        sa.column("margin_side"),
        sa.column("margin_top"),
        sa.column("slide_numbers"),
        sa.column("slides_count"),
    )
    op.bulk_insert(
        layouts,
        [
            {
                "id": f"system-{name.lower()}",
                "name": name,
                "type": "system",
                "canvas_id": DEFAULT_CANVAS,
                "align": align,
                "corner_radius": 24,
                "density": density,
                "footer_text": "",
                "margin_bottom": 96,
                "margin_side": 80,
                "margin_top": 96,
                "slide_numbers": True,
                "slides_count": 6,
                **stamp,
            }
            for name, (align, density) in SYSTEM_LAYOUTS.items()
        ],
    )
    fonts = sa.table(
        "fonts",
        sa.column("id"),
        sa.column("created_at"),
        sa.column("updated_at"),
        sa.column("family"),
        sa.column("category"),
        sa.column("source"),
    )
    op.bulk_insert(
        fonts,
        [
            {
                "id": f"bundled-{family.lower().replace(' ', '_')}",
                "family": family,
                "category": category,
                "source": "bundled",
                **stamp,
            }
            for family, category in BUNDLED_FONTS
        ],
    )
    palettes = sa.table(
        "palettes",
        sa.column("id"),
        sa.column("created_at"),
        sa.column("updated_at"),
        sa.column("name"),
        sa.column("type"),
        *[sa.column(f"{n}_{t}") for n in COLORS for t in ("light", "dark")],
    )
    rows: list[dict[str, Any]] = []
    for name, pairs in SYSTEM_PALETTES.items():
        row: dict[str, Any] = {"id": f"system-{name.lower()}", "name": name, "type": "system"}
        for color, (light, dark) in zip(COLORS, pairs, strict=True):
            row[f"{color}_light"], row[f"{color}_dark"] = light, dark
        rows.append({**row, **stamp})
    op.bulk_insert(palettes, rows)


def _stamped(values: list[dict[str, object]]) -> list[dict[str, object]]:
    now = _now()
    return [{"id": str(uuid.uuid4()), "created_at": now, "updated_at": now, **v} for v in values]


def _seed_analysis() -> None:
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
    ignored_rows: list[dict[str, object]] = [{"name": n, "reason": "never read"} for n in _IGNORED]

    for name, columns, rows in (
        (
            "directory_patterns",
            ("name", "purpose", "match_kind", "max_depth", "sort_order"),
            pattern_rows,
        ),
        (
            "monorepo_signals",
            ("ecosystem", "signal_kind", "file_name", "min_count", "description"),
            signal_rows,
        ),
        ("ignored_directories", ("name", "reason"), ignored_rows),
    ):
        table = sa.table(
            name,
            *[sa.column(c) for c in ("id", "created_at", "updated_at", *columns)],
        )
        op.bulk_insert(table, _stamped(rows))


def upgrade() -> None:
    _create_settings_and_ai()
    _create_brand_tables()
    _create_repository_tables()
    _create_readme_tables()
    _create_studio_tables()
    _seed_brand()
    _seed_analysis()
