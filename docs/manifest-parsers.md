# Project file parsers

When Kodalo reads a repository it finds the project files (`package.json`, `pyproject.toml`, `go.mod` and so on) and reads the package name, version, dependencies and dev dependencies out of them. How each kind of file is read is described by a small JSON config, not by code, so a new language or tool can be added without changing Kodalo.

## Where configs live

- **Bundled:** `src/kodalo/core/configs/parsers/*.json`, shipped with Kodalo.
- **Your own:** `parsers/*.json` inside the Kodalo data folder (`%LOCALAPPDATA%/Kodalo/parsers` on Windows, or the folder given with `--data-dir`). A config with the same `id` as a bundled one replaces it; any other `id` adds a new kind of file.
- A config that is not valid is skipped, and the reason is added to the repository's warnings. The others keep working.

## What a config holds

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

## The four formats

- **`json` and `toml`:** a `path` is dot separated keys (`project.name`); `*` matches every key of a table or every item of a list (`dependency-groups.*`). A dependency entry also has a `shape`: `keys` (the names are the keys of a table, as in `package.json`) or `requirements` (a list of strings such as `"typer>=0.9"`; the package name is taken from the start of each string).
- **`xml`:** a `path` is a simple element path from the root element (`dependencies/dependency/artifactId`, with `[child='text']` filters such as `dependency[scope='test']`). A final `/@Attribute` reads an attribute (`ItemGroup/PackageReference/@Include`). Namespaces are ignored. The shape is `values`.
- **`lines`:** for text files. `name` and `version` entries are regular expressions, and each dependency entry is `{ "regex": "...", "section": "..." }`. Every regular expression needs a group named `value` (`(?P<value>...)`), which is the text to keep. A `section` limits the match to the indented lines under a line that matches it (YAML-style blocks such as `dependencies:`).
- **`none`:** the file is listed as a project file and nothing more.

## Limits and safety

- Configs are data only; they can never run code.
- A project file larger than 200 KB is not read. File names that look like secrets (`.env*`, `*.pem`, `*.key`, anything with `secret` or `credential`) cannot be named in a config.
- Each list of dependencies keeps the first 50 names, with a warning when more exist.
- From GitHub, only the number of project files set in Settings, GitHub, "Project files to read" (default 10, at most 100) are read, top folders first, and a warning says when others were left out. A local folder is read in full.
- A file that cannot be read keeps its entry with empty details and a warning.

## Writing configs with AI

For top-level project files no config covers, `Refresh with AI` on the Repositories page (or `kodalo repositories add <repo> --refresh-with-ai`) asks the default AI connection and model for a config. The same instructions go to every provider: they are the bundled `src/kodalo/core/ai/prompts/repo/repo-analyzer.SKILL.md`, which doubles as a Claude Code skill file and also covers frameworks and tooling (see [framework-detection.md](framework-detection.md)), so one request and one answer serve all three. To keep cost low it sends at most 5 files, 1.5 KB each, caps the answer (700 tokens per file plus room for frameworks and tools, and the model's own max tokens when lower), and shows the estimate before sending. Replies must be JSON; each config is validated, must not reuse an existing `id`, and must read something from the real file before it is saved to `parsers/`.

## Adding a stack

1. Copy the closest bundled config to your `parsers` folder and change `id`, `ecosystem`, `files` and the paths or patterns.
2. Read a repository that has such a file (`kodalo repositories add <repo> --refresh`) and check the Project files table.
3. Fix the warnings if the file could not be read.
