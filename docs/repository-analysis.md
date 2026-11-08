# Repository analysis

How Kodalo reads a repository, in three layers. Each one builds on the one before and keeps its evidence.

1. [Project files](#project-files): the package name, version and dependencies in `package.json`, `pyproject.toml`, `go.mod` and similar files.
2. [Frameworks and tooling](#frameworks-and-tooling): the frameworks and tools those dependencies and the file list point to.
3. [README analysis](#readme-analysis): the purpose, installation methods, capabilities and use cases the README and its linked documents state.

The first two are described by small JSON configs, not code, so a new language, framework or tool can be added without changing Kodalo. Each layer has a free first pass and an optional `Refresh with AI`: one request that carries the project files and frameworks together, and one for the README.

## Project files

When Kodalo reads a repository it finds the project files (`package.json`, `pyproject.toml`, `go.mod` and so on) and reads the package name, version, dependencies and dev dependencies out of them. How each kind of file is read is described by a small JSON config, not by code, so a new language or tool can be added without changing Kodalo.

### Where configs live

- **Bundled:** `src/kodalo/core/configs/parsers/*.json`, shipped with Kodalo.
- **Your own:** `parsers/*.json` inside the Kodalo data folder (`%LOCALAPPDATA%/Kodalo/parsers` on Windows, or the folder given with `--data-dir`). A config with the same `id` as a bundled one replaces it; any other `id` adds a new kind of file.
- A config that is not valid is skipped, and the reason is added to the repository's warnings. The others keep working.

### What a config holds

```json
{
  "schema_version": 1,
  "id": "js-package",
  "ecosystem": "js",
  "priority": 100,
  "files": ["package.json"],
  "lockfiles": ["package-lock.json", "yarn.lock"],
  "format": "json",
  "name": ["name"],
  "version": ["version"],
  "dependencies": [{ "path": "dependencies", "shape": "keys" }],
  "dev_dependencies": [{ "path": "devDependencies", "shape": "keys" }],
  "exclude_dependencies": [],
  "dev_wins": false
}
```

| Field | Meaning |
| --- | --- |
| `schema_version` | Always `1`. |
| `id`, `ecosystem` | Lowercase letters, digits and dashes. `ecosystem` groups files for the monorepo check. |
| `priority` | Optional, 0 to 1000, lower is tried first when two configs match the same file name (default 100). |
| `files` | File names (wildcards such as `*.csproj` allowed, no folders) that are project files. |
| `lockfiles` | File names that are lockfiles. They are listed but never opened. |
| `format` | `json`, `toml`, `xml`, `lines` or `none` (list the file, read nothing). |
| `name`, `version` | Where to find them; the first one found wins. |
| `dependencies`, `dev_dependencies` | Where the package names are. |
| `exclude_dependencies` | Names or wildcards to leave out (for example `php`, `ext-*`). |
| `dev_wins` | When a name is in both lists, keep it only as a dev dependency (used for Maven's `test` scope). |

A config holds at most 20 entries per list, and each pattern at most 300 characters.

### The four formats

- **`json` and `toml`:** a `path` is dot separated keys (`project.name`); `*` matches every key of a table or every item of a list (`dependency-groups.*`). A dependency entry also has a `shape`: `keys` (the names are the keys of a table, as in `package.json`) or `requirements` (a list of strings such as `"typer>=0.9"`; the package name is taken from the start of each string).
- **`xml`:** a `path` is a simple element path from the root element (`dependencies/dependency/artifactId`, with `[child='text']` filters such as `dependency[scope='test']`). A final `/@Attribute` reads an attribute (`ItemGroup/PackageReference/@Include`). Namespaces are ignored. The shape is `values`.
- **`lines`:** for text files. `name` and `version` entries are regular expressions, and each dependency entry is `{ "regex": "...", "section": "..." }`. Every regular expression needs a group named `value` (`(?P<value>...)`), which is the text to keep. A `section` limits the match to the indented lines under a line that matches it (YAML-style blocks such as `dependencies:`).
- **`none`:** the file is listed as a project file and nothing more.

### Limits and safety

- Configs are data only; they can never run code.
- A project file larger than 200 KB is not read. File names that look like secrets (`.env*`, `*.pem`, `*.key`, anything with `secret` or `credential`) cannot be named in a config.
- Each list of dependencies keeps the first 50 names, with a warning when more exist.
- From GitHub, only the number of project files set in Settings, GitHub, "Project files to read" (default 10, at most 100) are read, top folders first, and a warning says when others were left out. A local folder is read in full.
- A file that cannot be read keeps its entry with empty details and a warning.

### Writing configs with AI

For top-level project files no config covers, `Refresh with AI` on the Repositories page (or `kodalo repositories add <repo> --refresh-with-ai`) asks the default AI connection and model for a config. The same instructions go to every provider: they are the bundled `src/kodalo/core/ai/prompts/repo/repo-analyzer.SKILL.md`, which doubles as a Claude Code skill file and also covers frameworks and tooling (see [Frameworks and tooling](#frameworks-and-tooling)), so one request and one answer serve all three. To keep cost low it sends at most 5 files, 1.5 KB each, caps the answer (700 tokens per file plus room for frameworks and tools, and the model's own max tokens when lower), and shows the estimate before sending. Replies must be JSON; each config is validated, must not reuse an existing `id`, and must read something from the real file before it is saved to `parsers/`.

### Adding a stack

1. Copy the closest bundled config to your `parsers` folder and change `id`, `ecosystem`, `files` and the paths or patterns.
2. Read a repository that has such a file (`kodalo repositories add <repo> --refresh`) and check the Project files table.
3. Fix the warnings if the file could not be read.

## Frameworks and tooling

Reading a repository (`kodalo repositories add`, or Studio in the window) also lists the frameworks it uses, such as FastAPI or React, and its tooling: build, test, lint and format, CI, container and package tools such as Make, pytest, Ruff, GitHub Actions, Docker or uv. Each one comes with its evidence: the project file and package that showed it (`pyproject.toml: "fastapi"`), or the file that did (`vite.config.ts`).

Detection runs on what is already read: the dependencies of the project files (see [Project files](#project-files)) and the repository's file list. Nothing extra is downloaded. Files inside ignored folders such as `node_modules` are not looked at, and lockfiles are never used as evidence.

### Where the rules live

- **Bundled:** `src/kodalo/core/configs/frameworks/*.json`, shipped with Kodalo (about 120 common frameworks).
- **Your own:** `frameworks/*.json` inside the Kodalo data folder (`%LOCALAPPDATA%/Kodalo/frameworks` on Windows, or the folder given with `--data-dir`). A framework with the same `id` as a bundled one replaces it; any other `id` adds a new one. A file that is not valid is skipped and mentioned in the repository's warnings.

Tooling works the same way with its own files: bundled `src/kodalo/core/configs/toolings/*.json` (about 80 common tools) and your own `tooling/*.json` in the data folder. A tooling file holds a `tools` list instead of `frameworks`, and its `category` is one of `build`, `test`, `lint_format`, `ci`, `containers` or `package_distribution`. A folder such as `.github/workflows` is matched with `paths`; a tool listed as a dev dependency (Ruff, ESLint) is matched with `dependencies`.

Configs hold only data, never code.

### Format

```json
{
  "schema_version": 1,
  "frameworks": [
    {
      "id": "vite",
      "name": "Vite",
      "category": "build",
      "ecosystems": ["js"],
      "dependencies": ["vite"],
      "files": ["vite.config.*"],
      "paths": []
    }
  ]
}
```

| Key | Meaning |
|---|---|
| `id` | Lowercase letters, digits and dashes. |
| `name` | The display name, at most 64 characters. |
| `category` | One of `web`, `ui`, `cli`, `data`, `testing`, `build`, `mobile`, `desktop`, `ml`, `other`. |
| `dependencies` | Package names. Case does not matter and `_` equals `-`; `*` is a wildcard (`@angular/*`). |
| `ecosystems` | Optional. Only match dependencies from these ecosystems (`js`, `python`, `jvm`, `go`, ...). Empty means any. |
| `files` | File or folder names (wildcards allowed) matched anywhere in the repository. |
| `paths` | Relative paths (`config/routes.rb`, `wp-content`) matched anywhere in the repository. |

Any one match is enough, and an entry needs at least one of `dependencies`, `files` or `paths`. At most 30 items per list. When several things match, the one in the top-most folder is the evidence.

### Teaching Kodalo more frameworks with the AI

Packages that no config recognises can be sent to your default AI model as part of `Refresh with AI` on the Repositories page, or `kodalo repositories add <repo> --refresh-with-ai`. This is one request that also carries the project-file step: Kodalo shows the combined expected tokens and asks once before sending (`--yes` skips the question). Packages that a newly saved parser reads from its file can also match a framework in the same answer, so there is no second question.

What is sent: only the package names that no framework or tooling config covers (at most 80, grouped by ecosystem), the names of up to 40 top-level files and folders, and up to 40 top-level names that look like configuration and that no tooling config covers (the `tool files:` line). File contents are never sent, and names that look like secrets are left out. The instructions are the bundled `src/kodalo/core/ai/prompts/repo/repo-analyzer.SKILL.md`, which holds the parser, framework and tooling instructions in one prompt and asks for one answer, `{"configs": [], "frameworks": [], "tools": []}`.

The ids Kodalo already recognised in the repository are listed in the question (`already known:`) so the model does not repeat them; if it does, the repeat is dropped silently. Each run is added to the AI history (Settings > AI History), with its tokens.

The answer must be JSON. Each entry is validated like a hand-written one, must not reuse an existing `id`, and must match something that was actually sent. Valid entries are saved one per file in the `frameworks` folder (frameworks) or the `tooling` folder (tools), and the repository is read again to use them. One answer can hold both a `frameworks` and a `tools` list.

### Adding your own

1. Copy the closest bundled file into your `frameworks` folder.
2. Change the `id`, `name`, `category` and the names to match.
3. Run `kodalo repositories add <repo> --refresh`. Problems are shown as warnings.

### Documentation, files not read and evidence

Reading a repository also records, without any AI:

- **Documentation**: the README, changelog (`CHANGELOG`, `CHANGES`, `HISTORY`, `NEWS`), `CONTRIBUTING`, license (`LICENSE`, `COPYING`), `CODE_OF_CONDUCT` and `SECURITY` files at the top level, and the docs folder (`docs`, `doc` or `documentation`), found by name only. Nothing is opened.
- **Not read**: project files that were left out, each with a reason: `secret` (names such as `.env*`, `*.pem`, `*.key`, `id_rsa*`; never opened) or `too large or unreadable` (over 200 KB, binary, or the read failed).
- **Evidence for project files**: the first line (at most 120 characters) of each project file that holds its package name, or its first dependency.

The AI only writes parser and framework configs, and each one is already tried on the real file before it is saved, so those are not given evidence of their own.

## README analysis

Studio's Analyze step reads a repository's README and the documents it links to, and keeps what they say: the purpose, the documented ways to install, and the capabilities. A first pass needs no AI; `Refresh with AI` reads the same documents with the default AI model for a cleaner result and the use cases.

### What is read

The documents come from the repository analysis already stored (the README names and the docs folder found by name), so nothing that analysis found is fetched again. The files are read with the way chosen in the GitHub setting (the `gh` CLI, web fetch or the local folder).

1. Every README is read first.
2. The relative Markdown links found in the READMEs are read one level deep. Links inside a linked document are not followed. External addresses, anchors, images and links outside the repository are ignored. Links into the docs folder go first.
3. Some files are skipped with a reason: secret-looking files, `CHANGELOG`, `LICENSE`, `CONTRIBUTING`, `SECURITY` and `CODE_OF_CONDUCT` (not about using the product), generated reference pages (a name containing `reference`), files that could not be read, and anything over the document limit.

Two settings (GitHub settings, `kodalo settings github set`) bound the work:

| Setting | Default | Range |
| --- | --- | --- |
| Documents to read (`document_limit`) | 10 | 1 to 50 |
| Most of each document to read (`document_max_kb`) | 200 KB | 1 to 2000 |

A document over the size limit is cut and a warning says so.

### What is found without AI

| Result | How |
| --- | --- |
| Purpose | The first paragraph of the first README (badges, lists and tables are passed over); the tagline is its first sentence. When the README has no introduction the repository description is used and a warning says so. |
| Installation | Code blocks in sections titled install, getting started, quick start, download or setup: a line that starts with a known command (pip, pipx, uv, npm, yarn, pnpm, Homebrew, Scoop, winget, Chocolatey, apt, dnf, dpkg, rpm, cargo, go, gem, Docker, an install script, `git clone`). A line about an installer download in prose is listed as `Installer`. Identical commands are listed once. |
| Capabilities | Bullets under headings such as features, capabilities, commands, highlights and roadmap, as `**Name**: description`, `Name: description`, `Name - description` or the first words. At most 30. An item that is under a roadmap heading, or says planned, coming soon, not yet or experimental, carries the note `Planned or experimental`. |
| Documents | Every document read or skipped, with the reason. |

Each installation method and capability carries evidence: the file and a quote of at most 120 characters, with the status `documented`. Nothing is listed without a quote.

### Refresh with AI

The fixed rules above depend on how a README is laid out, and documents differ, so the AI can read the documents itself. The request is shown first and sent only after confirmation (the window's `Proceed`, the command line's question, or `--yes`): the list of documents and the expected tokens. It holds the text of the documents the first pass read, read again with the same limits, with lines that look like secrets removed, and nothing else. The prompt is `src/kodalo/core/ai/prompts/repo/readme-analyzer.SKILL.md`.

The model returns the purpose, the installation methods, the capabilities, the features and the use cases. Nothing without evidence is kept:

- An installation method or capability is saved only when its quote (at most 120 characters) is found in the file it names. Whitespace and case are ignored when comparing.
- A use case is saved only when every capability it names was saved. Its evidence is the first of those capabilities, with the status `inferred`.
- A feature is saved only when every capability it names was saved, like a use case. Its `importance` (`headline`, `supporting`, `minor`) and `maturity` (`stable`, `experimental`, `planned`, `unspecified`) fall back to `supporting` and `unspecified` when the model gives anything else. Its `use_cases` keep only titles of saved use cases. Its `claims` (`number`, `absolute`, `comparison`, `performance`, `compatibility`; at most 5) are kept only when their text is found in one of the documents sent; Studio shows them as "Repeat with care".
- The purpose is kept when it has a summary; its file must be one of the documents sent.
- The icon: when the repository was read, image files named like an icon, logo, favicon, brand or mark were noted as candidates (at most 20, near the top first, vector images before bitmaps). They are sent after the documents under `### Icon candidates`, and the model names the one that is the product's own icon, or none. The path must be one of the candidates and the file must be a PNG, JPEG, WebP or SVG of at most 2 MB; it is then copied into the data folder (`repo_icons`). Whatever the answer, the repository is marked as looked at, so "looked at, none kept" means no icon was found and nothing is made up. Designs use it when Settings > Platforms has Use repo icon on.
- A part the model left empty, or whose items all failed these checks, keeps what was found before. What was left out is listed with the reason.

The call is added to the AI history with the purpose `studio`.

### Storage

The analysis is kept in six tables (migrations `0017`, `0018` and `0019`): `repository_readmes` (purpose, warnings and when it was read), `repository_documents`, `repository_installs`, `repository_capabilities`, `repository_features` and `repository_use_cases`. Reading again (Refresh) replaces the documents, installation methods and capabilities with the first-pass result and keeps the features and use cases; press `Refresh with AI` again to rewrite them all. Deleting a repository deletes its analysis.

### Where it lives

| Layer | Where |
| --- | --- |
| Core | `kodalo.core.repositories.readme` (`ReadmeService`) and `kodalo.core.repositories.ai.readme` (`ReadmeAssistant`, which plans before it sends) |
| Command line | `kodalo repositories add --readme [--readme-with-ai] [--yes]`; see [cli.md](cli.md) |
| API | `/api/v1/studio/repositories/{id}/readme` and `.../readme/analysis`; see [api.md](api.md) |
| Window | The Analyze step of Studio, `pages/ReadmeView.jsx`; see [ui.md](ui.md) |

### Refreshing after the AI

Once the AI has written an analysis, a plain refresh (`POST .../readme` with `refresh`, or `readme --refresh`) does not replace it. It keeps the purpose, installation methods and capabilities as they are. It adds installation methods that are new in the documents (matched by method and command), fills a blank capability description from the documents when the name matches, and updates the list of documents read. It adds no capabilities of its own: the plain read takes every bullet it finds, and the AI chose which ones matter. Before the AI has run, a refresh replaces what was found, as before.
