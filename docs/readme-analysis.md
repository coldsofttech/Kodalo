# README analysis

Studio's Analyze step reads a repository's README and the documents it links to, and keeps what they say: the purpose, the documented ways to install, and the capabilities. A first pass needs no AI; `Refresh with AI` reads the same documents with the default AI model for a cleaner result and the use cases.

## What is read

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

## What is found without AI

| Result | How |
| --- | --- |
| Purpose | The first paragraph of the first README (badges, lists and tables are passed over); the tagline is its first sentence. When the README has no introduction the repository description is used and a warning says so. |
| Installation | Code blocks in sections titled install, getting started, quick start, download or setup: a line that starts with a known command (pip, pipx, uv, npm, yarn, pnpm, Homebrew, Scoop, winget, Chocolatey, apt, dnf, dpkg, rpm, cargo, go, gem, Docker, an install script, `git clone`). A line about an installer download in prose is listed as `Installer`. Identical commands are listed once. |
| Capabilities | Bullets under headings such as features, capabilities, commands, highlights and roadmap, as `**Name**: description`, `Name: description`, `Name - description` or the first words. At most 30. An item that is under a roadmap heading, or says planned, coming soon, not yet or experimental, carries the note `Planned or experimental`. |
| Documents | Every document read or skipped, with the reason. |

Each installation method and capability carries evidence: the file and a quote of at most 120 characters, with the status `documented`. Nothing is listed without a quote.

## Refresh with AI

The fixed rules above depend on how a README is laid out, and documents differ, so the AI can read the documents itself. The request is shown first and sent only after confirmation (the window's `Proceed`, the command line's question, or `--yes`): the list of documents and the expected tokens. It holds the text of the documents the first pass read, read again with the same limits, with lines that look like secrets removed, and nothing else. The prompt is `src/kodalo/core/ai/prompts/repo/readme-analyzer.SKILL.md`.

The model returns the purpose, the installation methods, the capabilities, the features and the use cases. Nothing without evidence is kept:

- An installation method or capability is saved only when its quote (at most 120 characters) is found in the file it names. Whitespace and case are ignored when comparing.
- A use case is saved only when every capability it names was saved. Its evidence is the first of those capabilities, with the status `inferred`.
- A feature is saved only when every capability it names was saved, like a use case. Its `importance` (`headline`, `supporting`, `minor`) and `maturity` (`stable`, `experimental`, `planned`, `unspecified`) fall back to `supporting` and `unspecified` when the model gives anything else. Its `use_cases` keep only titles of saved use cases. Its `claims` (`number`, `absolute`, `comparison`, `performance`, `compatibility`; at most 5) are kept only when their text is found in one of the documents sent; Studio shows them as "Repeat with care".
- The purpose is kept when it has a summary; its file must be one of the documents sent.
- The icon: when the repository was read, image files named like an icon, logo, favicon, brand or mark were noted as candidates (at most 20, near the top first, vector images before bitmaps). They are sent after the documents under `### Icon candidates`, and the model names the one that is the product's own icon, or none. The path must be one of the candidates and the file must be a PNG, JPEG, WebP or SVG of at most 2 MB; it is then copied into the data folder (`repo_icons`). Whatever the answer, the repository is marked as looked at, so "looked at, none kept" means no icon was found and nothing is made up. Designs use it when Settings > Platforms has Use repo icon on.
- A part the model left empty, or whose items all failed these checks, keeps what was found before. What was left out is listed with the reason.

The call is added to the AI history with the purpose `studio`.

## Storage

The analysis is kept in six tables (migrations `0017`, `0018` and `0019`): `repository_readmes` (purpose, warnings and when it was read), `repository_documents`, `repository_installs`, `repository_capabilities`, `repository_features` and `repository_use_cases`. Reading again (Refresh) replaces the documents, installation methods and capabilities with the first-pass result and keeps the features and use cases; press `Refresh with AI` again to rewrite them all. Deleting a repository deletes its analysis.

## Where it lives

| Layer | Where |
| --- | --- |
| Core | `kodalo.core.repositories.readme` (`ReadmeService`) and `kodalo.core.repositories.ai.readme` (`ReadmeAssistant`, which plans before it sends) |
| Command line | `kodalo repositories add --readme [--readme-with-ai] [--yes]`; see [cli.md](cli.md) |
| API | `/api/v1/studio/repositories/{id}/readme` and `.../readme/analysis`; see [api.md](api.md) |
| Window | The Analyze step of Studio, `pages/ReadmeView.jsx`; see [ui.md](ui.md) |

## Refreshing after the AI

Once the AI has written an analysis, a plain refresh (`POST .../readme` with `refresh`, or `readme --refresh`) does not replace it. It keeps the purpose, installation methods and capabilities as they are. It adds installation methods that are new in the documents (matched by method and command), fills a blank capability description from the documents when the name matches, and updates the list of documents read. It adds no capabilities of its own: the plain read takes every bullet it finds, and the AI chose which ones matter. Before the AI has run, a refresh replaces what was found, as before.
