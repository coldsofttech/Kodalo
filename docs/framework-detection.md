# Framework detection

Reading a repository (`kodalo repositories add`, or Studio in the window) also lists the frameworks it uses, such as FastAPI or React, and its tooling: build, test, lint and format, CI, container and package tools such as Make, pytest, Ruff, GitHub Actions, Docker or uv. Each one comes with its evidence: the project file and package that showed it (`pyproject.toml: "fastapi"`), or the file that did (`vite.config.ts`).

Detection runs on what is already read: the dependencies of the project files (see [manifest-parsers.md](manifest-parsers.md)) and the repository's file list. Nothing extra is downloaded. Files inside ignored folders such as `node_modules` are not looked at, and lockfiles are never used as evidence.

## Where the rules live

- **Bundled:** `src/kodalo/core/configs/frameworks/*.json`, shipped with Kodalo (about 120 common frameworks).
- **Your own:** `frameworks/*.json` inside the Kodalo data folder (`%LOCALAPPDATA%/Kodalo/frameworks` on Windows, or the folder given with `--data-dir`). A framework with the same `id` as a bundled one replaces it; any other `id` adds a new one. A file that is not valid is skipped and mentioned in the repository's warnings.

Tooling works the same way with its own files: bundled `src/kodalo/core/configs/toolings/*.json` (about 80 common tools) and your own `tooling/*.json` in the data folder. A tooling file holds a `tools` list instead of `frameworks`, and its `category` is one of `build`, `test`, `lint_format`, `ci`, `containers` or `package_distribution`. A folder such as `.github/workflows` is matched with `paths`; a tool listed as a dev dependency (Ruff, ESLint) is matched with `dependencies`.

Configs hold only data, never code.

## Format

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

## Teaching Kodalo more frameworks with the AI

Packages that no config recognises can be sent to your default AI model as part of `Refresh with AI` on the Repositories page, or `kodalo repositories add <repo> --refresh-with-ai`. This is one request that also carries the project-file step: Kodalo shows the combined expected tokens and asks once before sending (`--yes` skips the question). Packages that a newly saved parser reads from its file can also match a framework in the same answer, so there is no second question.

What is sent: only the package names that no framework or tooling config covers (at most 80, grouped by ecosystem), the names of up to 40 top-level files and folders, and up to 40 top-level names that look like configuration and that no tooling config covers (the `tool files:` line). File contents are never sent, and names that look like secrets are left out. The instructions are the bundled `src/kodalo/core/ai/prompts/repo/repo-analyzer.SKILL.md`, which holds the parser, framework and tooling instructions in one prompt and asks for one answer, `{"configs": [], "frameworks": [], "tools": []}`.

The ids Kodalo already recognised in the repository are listed in the question (`already known:`) so the model does not repeat them; if it does, the repeat is dropped silently. Each run is added to the AI history (Settings > AI History), with its tokens.

The answer must be JSON. Each entry is validated like a hand-written one, must not reuse an existing `id`, and must match something that was actually sent. Valid entries are saved one per file in the `frameworks` folder (frameworks) or the `tooling` folder (tools), and the repository is read again to use them. One answer can hold both a `frameworks` and a `tools` list.

## Adding your own

1. Copy the closest bundled file into your `frameworks` folder.
2. Change the `id`, `name`, `category` and the names to match.
3. Run `kodalo repositories add <repo> --refresh`. Problems are shown as warnings.

## Documentation, files not read and evidence

Reading a repository also records, without any AI:

- **Documentation**: the README, changelog (`CHANGELOG`, `CHANGES`, `HISTORY`, `NEWS`), `CONTRIBUTING`, license (`LICENSE`, `COPYING`), `CODE_OF_CONDUCT` and `SECURITY` files at the top level, and the docs folder (`docs`, `doc` or `documentation`), found by name only. Nothing is opened.
- **Not read**: project files that were left out, each with a reason: `secret` (names such as `.env*`, `*.pem`, `*.key`, `id_rsa*`; never opened) or `too large or unreadable` (over 200 KB, binary, or the read failed).
- **Evidence for project files**: the first line (at most 120 characters) of each project file that holds its package name, or its first dependency.

The AI only writes parser and framework configs, and each one is already tried on the real file before it is saved, so those are not given evidence of their own.
