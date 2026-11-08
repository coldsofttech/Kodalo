"""Show a repository and its README analysis."""

import dataclasses

from rich.table import Table

from kodalo.cli import output
from kodalo.core.repositories import Documentation, Manifest, ReadmeAnalysis, RepoInfo


def manifest_text(manifest: Manifest) -> str:
    count = len(manifest.dependencies) + len(manifest.dev_dependencies)
    return f"{manifest.path} ({count} dependencies)" if count else manifest.path


def documentation_text(docs: Documentation) -> str:
    found = [
        *docs.readmes,
        docs.changelog,
        docs.contributing,
        docs.license_file,
        docs.code_of_conduct,
        docs.security,
        f"{docs.docs_dir}/" if docs.docs_dir else "",
    ]
    return ", ".join(name for name in found if name) or "-"


def show_repo(info: RepoInfo, as_json: bool) -> None:
    if as_json:
        data = dataclasses.asdict(info)
        del data["paths"]  # only used while reading
        output.console.print_json(data=data)
        return
    table = Table(show_header=False, title=f"{info.owner}/{info.name}")
    for label, value in (
        ("URL", info.url),
        ("Description", info.description or "-"),
        ("Homepage", info.homepage or "-"),
        ("Default branch", info.default_branch or "-"),
        ("License", info.license or "-"),
        ("Topics", ", ".join(info.topics) or "-"),
        ("Private / fork / archived", f"{info.is_private} / {info.is_fork} / {info.is_archived}"),
        ("Last pushed", info.last_pushed_at or "-"),
        ("Files", str(info.file_count)),
        ("Read with", info.access_method),
        ("Top level", ", ".join(e.path + ("/" if e.type == "dir" else "") for e in info.top_level)),
        ("Notable folders", ", ".join(f"{d.path} ({d.purpose})" for d in info.notable_dirs) or "-"),
        (
            "Project files",
            ", ".join(manifest_text(m) for m in info.manifests if not m.is_lockfile) or "-",
        ),
        ("Frameworks", ", ".join(f"{f.name} ({f.category})" for f in info.frameworks) or "-"),
        ("Tooling", ", ".join(f"{t.name} ({t.category})" for t in info.tooling) or "-"),
        ("Monorepo", ", ".join(info.monorepo_signals) if info.is_monorepo else "No"),
        ("Documentation", documentation_text(info.documentation)),
        ("Not read", ", ".join(f"{s.path} ({s.reason})" for s in info.skipped) or "-"),
    ):
        table.add_row(label, value)
    output.console.print(table)
    languages = Table("Language", "Bytes", "Percent")
    for language in info.languages:
        languages.add_row(language.name, str(language.bytes), f"{language.percent:.1f}")
    output.console.print(languages)
    for warning in info.warnings:
        output.err_console.print(f"[yellow]{warning}[/yellow]")


def show_readme(info: RepoInfo, analysis: ReadmeAnalysis, as_json: bool) -> None:
    if as_json:
        data = dataclasses.asdict(info)
        del data["paths"]  # only used while reading
        output.console.print_json(data={"repository": data, "readme": dataclasses.asdict(analysis)})
        return
    show_repo(info, False)
    purpose = Table(show_header=False, title="Purpose")
    purpose.add_row("Tagline", analysis.tagline or "-")
    purpose.add_row("Summary", analysis.summary or "-")
    output.console.print(purpose)
    for title, headers, rows in (
        (
            "Installation",
            ("Method", "Command", "Found in"),
            [(i.method, i.command or "-", i.evidence.file or "-") for i in analysis.installation],
        ),
        (
            "Capabilities",
            ("Capability", "Description", "Note", "Found in"),
            [
                (c.name, c.description or "-", c.note or "-", c.evidence.file or "-")
                for c in analysis.capabilities
            ],
        ),
        (
            "Features",
            ("Feature", "Importance", "Maturity", "Description", "Careful with"),
            [
                (
                    f.name,
                    f.importance,
                    f.maturity,
                    f.description or "-",
                    "; ".join(c.text for c in f.claims) or "-",
                )
                for f in analysis.features
            ],
        ),
        (
            "Use cases",
            ("Use case", "Description", "Based on"),
            [(u.title, u.description or "-", u.evidence.quote or "-") for u in analysis.use_cases],
        ),
        (
            "Documents",
            ("Document", "Status", "Reason"),
            [(d.path, d.status, d.reason or "-") for d in analysis.documents],
        ),
    ):
        table = Table(*headers, title=title)
        for row in rows:
            table.add_row(*row)
        output.console.print(table)
    for warning in analysis.warnings:
        output.err_console.print(f"[yellow]{warning}[/yellow]")
