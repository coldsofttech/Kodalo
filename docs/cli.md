# CLI

`kodalo` is the command line of Kodalo, built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/). It reads repositories, manages brand profiles and settings, and runs the same studio steps (ideas, copy, design) as the window. This page is the complete reference: every command, argument and option.

- [Running](#running)
- [Global options](#global-options)
- [Commands](#commands)
- [Output conventions](#output-conventions)
- [Exit codes](#exit-codes)
- [Errors](#errors)
- [Adding a command](#adding-a-command)

## Running

```bash
kodalo --help                       # installed script
python -m kodalo.cli                # without relying on the script being on PATH
uvx --from Kodalo kodalo --help     # one-off, no install
kodalo <command> --help             # help for one command or group
```

## Global options

These go before the command name, for example `kodalo --quiet brand list`.

| Option | Short | Description |
| --- | --- | --- |
| `--help` | | Show help for the tool or for a command. |
| `--version` | `-V` | Show the version and exit. |
| `--verbose` | `-v` | Show extra detail on stderr, and a traceback for unexpected errors. |
| `--quiet` | `-q` | Only show errors. Cannot be combined with `--verbose`. |
| `--no-color` | | Disable colored output. The standard `NO_COLOR` variable has the same effect. |
| `--data-dir` | | Folder for the database and logos. Default: `%LOCALAPPDATA%/Kodalo`. |
| `--install-completion` | | Install shell completion for the current shell. |
| `--show-completion` | | Print the completion script instead of installing it. |

Every option is a command-line flag; the command reads no environment variables of its own.

## Commands

| Group | What it is for |
| --- | --- |
| [`doctor`](#doctor) | Check the installation and the local data |
| [`repositories`](#repositories) | Add, check, list, show and remove repositories |
| [`studio`](#studio) | Make a post from a repository: ideas, copy, design |
| [`brand`](#brand) | Brand profiles, palettes, layouts, canvases, logos and fonts |
| [`settings`](#settings) | GitHub access, AI connections, logs and platform settings |

In the tables, **Value** is the kind of value an option takes (empty for a flag) and `<arg>` is required while `[arg]` is optional. Options for the same command can be given in any order. Commands that ask the AI print what would be sent and the expected tokens, then ask first; `--yes` skips the question.

### `doctor`

Diagnose the installation and the local data without changing anything: the Kodalo and Python versions, the platform, the required libraries, the data folder, the database (its version, or that it is not created yet), the number of brand profiles and the fonts available. Each line is `ok`, `warn` (optional) or `FAIL` (required). Exits with 1 if a required check fails, for example a database written by a newer Kodalo. Add `--json` for `{"healthy": ..., "checks": [...]}`.

```text
kodalo doctor [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

### `repositories`

Add, check, list, show and remove the repositories Kodalo keeps. How a repository is reached is chosen with `settings github`. The project files read are described in [project files](repository-analysis.md#project-files), frameworks and tooling in [frameworks and tooling](repository-analysis.md#frameworks-and-tooling) and the README analysis in [README analysis](repository-analysis.md#readme-analysis).

#### `repositories check`

Check a folder or address against the GitHub mode. Exits with 1 when it is not valid.

```text
kodalo repositories check <value> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `repositories add`

Add a repository: read its metadata, languages and structure, and keep them.

```text
kodalo repositories add <value> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--refresh` |  |  | Read again, even if added. |
| `--owner` | text |  | Local folder: the owner (required once). |
| `--repo` | text |  | Local folder: the repository name. |
| `--license` | text |  | Local folder: the license, e.g. MIT. |
| `--branch` | text |  | Local folder: the default branch. |
| `--description` | text |  | Local folder: a short description. |
| `--homepage` | text |  | Local folder: the home page address. |
| `--topic` | text |  | Local folder: a topic; repeatable. |
| `--private` |  |  | Local folder: it is private. |
| `--fork` |  |  | Local folder: it is a fork. |
| `--archived` |  |  | Local folder: it is archived. |
| `--refresh-with-ai` |  |  | Ask the default AI model to read unknown project files and find frameworks. |
| `--yes` / `-y` |  |  | With an AI option: do not ask before sending. |
| `--readme` |  |  | Also read the README and the docs it links to: purpose, installation, capabilities. Without AI. Kept; --refresh reads it again. |
| `--readme-with-ai` |  |  | Ask the default AI model to read those documents and write the purpose, installation, capabilities and use cases (implies --readme). |
| `--json` |  |  | Output as JSON. |

#### `repositories list`

List the added repositories.

```text
kodalo repositories list [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `repositories show`

Show an added repository.

```text
kodalo repositories show <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `repositories remove`

Remove a repository and everything saved about it (analysis, features, ideas).

```text
kodalo repositories remove <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--yes` / `-y` |  |  | Do not ask for confirmation. |

### `studio`

Make a post from an added repository, step by step: ideas, then copy, then design. Checking, reading and analyzing a repository is done with `repositories`. Every step takes the repository id, and the steps after ideas also take the brand (`--brand`, name or id; its canvas must be for Instagram) and the idea (`--idea`, for example `idea-1`; `--hook` picks another hook). A tool post is the default; for a feature post add `--type feature`, `--kind` (`features`, `use_cases` or `capabilities`) and `--name`. Commands that ask the AI print what would be sent and the expected tokens, then ask first; `--yes` skips the question. `--json` prints machine-readable output. A command that shows something saved exits with 1 when nothing was made yet.

#### `studio ideas`

Plan, make and show the post ideas of a repository.

##### `studio ideas plan`

Say what the AI would be sent and what it costs. Nothing is sent.

```text
kodalo studio ideas plan <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--json` |  |  | Output as JSON. |

##### `studio ideas make`

Ask the AI for a strategy, three angles and post ideas. New ones are added to the saved.

```text
kodalo studio ideas make <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--yes` / `-y` |  |  | Do not ask before sending to the AI. |
| `--json` |  |  | Output as JSON. |

##### `studio ideas show`

Show the saved post ideas. Exits with 1 when none were made yet.

```text
kodalo studio ideas show <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--json` |  |  | Output as JSON. |

#### `studio copy`

Plan, write, show and edit the copy of a post idea.

##### `studio copy plan`

Say what the AI would be sent and what it costs. Nothing is sent.

```text
kodalo studio copy plan <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--json` |  |  | Output as JSON. |

##### `studio copy make`

Ask the default AI model to write the copy of an idea. Replaces the copy saved before.

```text
kodalo studio copy make <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--yes` / `-y` |  |  | Do not ask before sending to the AI. |
| `--json` |  |  | Output as JSON. |

##### `studio copy show`

Show the saved copy. Exits with 1 when none was written yet.

```text
kodalo studio copy show <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--json` |  |  | Output as JSON. |

##### `studio copy edit`

Replace the saved copy with your edited text (slides, caption, alternative opening and
hashtags); the limits are applied.

```text
kodalo studio copy edit <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--file` / `-f` | file |  | JSON as from: copy show --json. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--json` |  |  | Output as JSON. |

#### `studio design`

Plan, make and show the design of a written post, and export its slides.

##### `studio design plan`

Say what the AI would be sent to design the saved copy. Nothing is sent.

```text
kodalo studio design plan <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--json` |  |  | Output as JSON. |

##### `studio design make`

Ask the default AI model how to lay out each slide of the saved copy. Replaces the
design saved before.

```text
kodalo studio design make <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--yes` / `-y` |  |  | Do not ask before sending to the AI. |
| `--json` |  |  | Output as JSON. |

##### `studio design show`

Show the saved design. Exits with 1 when none was made yet.

```text
kodalo studio design show <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--json` |  |  | Output as JSON. |

##### `studio design slide`

Export one slide as a self-contained HTML page (to stdout without --output).

```text
kodalo studio design slide <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--slide` | int range |  | The slide, from 0. |
| `--mode` | `light` `dark` | `light` | The brand's colors to use. |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--output` / `-o` | file |  | Write to a file. |

##### `studio design svg`

Export the drawing the AI made for one slide as SVG (to stdout without --output).

```text
kodalo studio design svg <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--slide` | int range |  | The slide, from 0. |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--output` / `-o` | file |  | Write to a file. |

##### `studio design export`

Make a picture of every slide and write them, with a caption.txt, into a new folder inside
--folder, to post by hand. Nothing is sent to Instagram. Needs Microsoft Edge.

```text
kodalo studio design export <repo_id> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--brand` / `-b` | text |  | The brand (name or id) the post is for. (required) |
| `--idea` | text |  | The post idea, e.g. idea-1. (required) |
| `--folder` | directory |  | An existing folder. The post goes into a new one. (required) |
| `--mode` | `light` `dark` | `light` | The brand's colors to use. |
| `--type` / `-t` | `tool` `feature` | `tool` | The kind of post: about the whole tool or one feature. |
| `--kind` | `features` `use_cases` `capabilities` |  | Feature post: which list the focus is in. |
| `--name` | text |  | Feature post: the name of the focus. |
| `--hook` | text |  | The hook to open with; the idea's own when left out. |
| `--json` |  |  | Output as JSON. |

### `brand`

Manage brand profiles, and the palettes, layouts and canvases they are built from. Every command takes a profile, palette, layout or canvas by name (any case) or by id. Messages go to stderr and `--quiet` hides them; data goes to stdout. Built-in palettes, layouts and canvases can be copied but not changed. Palettes, layouts and canvases are also served by the API under `/api/v1/brands/...`.

#### `brand list`

List brand profiles.

```text
kodalo brand list [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `brand show`

Show every setting of a profile.

```text
kodalo brand show <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `brand create`

Create a profile from a palette.

```text
kodalo brand create <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--palette` | text | `midnight` | Palette name or id to start from. See: brand palette list |
| `--default` |  |  | Make it the default. |

#### `brand rename`

Rename a profile.

```text
kodalo brand rename <name> <new_name>
```

#### `brand delete`

Delete a profile and its logo files.

```text
kodalo brand delete <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--yes` / `-y` |  |  | Do not ask for confirmation. |

#### `brand default`

Make a profile the default.

```text
kodalo brand default <name>
```

#### `brand duplicate`

Copy a profile, including its logo files.

```text
kodalo brand duplicate <name> <new_name>
```

#### `brand check`

Check the contrast of a profile's colors.

```text
kodalo brand check <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--strict` |  |  | Exit with 1 if any check fails. |
| `--json` |  |  | Output as JSON. |

#### `brand fonts`

List the fonts a profile can use (the font catalogue).

```text
kodalo brand fonts [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--system` / `--bundled` |  | `True` | Include installed fonts (default) or not. |
| `--json` |  |  | Output as JSON. |

#### `brand export`

Export a profile, with its logos, as JSON (to a file, or to the screen).

```text
kodalo brand export <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--output` / `-o` | file |  | Write to a file. |

#### `brand import`

Import a profile from a JSON file made by `export`.

```text
kodalo brand import <file> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--name` | text |  | Name for the new profile. |

#### `brand logo`

Set or remove a profile's logo.

##### `brand logo set`

Set a profile's logo from a PNG or SVG file.

```text
kodalo brand logo set <name> <file> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--dark` |  |  | Use it as the dark-mode logo. |

##### `brand logo remove`

Remove a profile's logo.

```text
kodalo brand logo remove <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--dark` |  |  | Remove the dark-mode logo. |

#### `brand settings`

List and change the settings of a profile.

##### `brand settings set`

Change one setting. Run `brand settings list NAME` to see the paths you can use.

```text
kodalo brand settings set <name> <path> <value>
```

##### `brand settings list`

List the settings of a profile that `settings set` accepts, with their values.

```text
kodalo brand settings list <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `brand layout`

Manage layouts: named slide settings (canvas, margins, text, slide count) brands share.

##### `brand layout list`

List layouts: the built-in ones first, then yours.

```text
kodalo brand layout list [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand layout show`

Show every setting of a layout and the brands that use it.

```text
kodalo brand layout show <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand layout add`

Create a layout from another layout. Change it afterwards with `layout set`.

```text
kodalo brand layout add <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--from-layout` | text |  | Start from this layout (default: Default). |

##### `brand layout set`

Change one setting of a layout of your own. Brands using it follow the change.

```text
kodalo brand layout set <name> <path> <value>
```

##### `brand layout settings`

List the settings that `layout set` accepts, with their values.

```text
kodalo brand layout settings <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand layout rename`

Rename a layout of your own.

```text
kodalo brand layout rename <name> <new_name>
```

##### `brand layout duplicate`

Copy a layout, built in or not, as a layout of your own.

```text
kodalo brand layout duplicate <name> <new_name>
```

##### `brand layout delete`

Delete a layout that no brand uses.

```text
kodalo brand layout delete <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--yes` / `-y` |  |  | Do not ask for confirmation. |

##### `brand layout export`

Export a layout, with its canvas, as JSON (to a file, or to the screen).

```text
kodalo brand layout export <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--output` / `-o` | file |  | Write to a file. |

##### `brand layout import`

Import a layout from a JSON file made by `layout export`.

```text
kodalo brand layout import <file> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--name` | text |  | Name for the new layout. |

#### `brand palette`

Manage palettes: named sets of brand colors that new brands start from.

##### `brand palette list`

List palettes: the built-in ones first, then yours.

```text
kodalo brand palette list [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand palette show`

Show every color of a palette.

```text
kodalo brand palette show <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand palette add`

Create a palette from a brand's colors or another palette (default: Midnight).

```text
kodalo brand palette add <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--from-brand` | text |  | Take the colors of this brand. |
| `--from-palette` | text |  | Start from this palette. |

##### `brand palette set`

Change one color of a palette of your own.

```text
kodalo brand palette set <name> <path> <value>
```

##### `brand palette rename`

Rename a palette of your own.

```text
kodalo brand palette rename <name> <new_name>
```

##### `brand palette duplicate`

Copy a palette, built in or not, as a palette of your own.

```text
kodalo brand palette duplicate <name> <new_name>
```

##### `brand palette delete`

Delete a palette of your own. Brands made from it keep their colors.

```text
kodalo brand palette delete <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--yes` / `-y` |  |  | Do not ask for confirmation. |

##### `brand palette export`

Export a palette as JSON (to a file, or to the screen).

```text
kodalo brand palette export <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--output` / `-o` | file |  | Write to a file. |

##### `brand palette import`

Import a palette from a JSON file made by `palette export`.

```text
kodalo brand palette import <file> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--name` | text |  | Name for the new palette. |

#### `brand canvas`

Manage canvases: named slide sizes that brand layouts reuse.

##### `brand canvas list`

List canvases: the built-in ones first, then yours.

```text
kodalo brand canvas list [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand canvas show`

Show one canvas and the brands that use it.

```text
kodalo brand canvas show <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `brand canvas add`

Create a canvas.

```text
kodalo brand canvas add <name> <width> <height>
```

##### `brand canvas edit`

Rename or resize a canvas. Every brand that uses it follows the change.

```text
kodalo brand canvas edit <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--name` | text |  | New name. |
| `--width` | number |  | New width in pixels. |
| `--height` | number |  | New height in pixels. |

##### `brand canvas duplicate`

Copy a canvas, built in or not, as a canvas of your own.

```text
kodalo brand canvas duplicate <name> <new_name>
```

##### `brand canvas delete`

Delete a canvas that no brand uses.

```text
kodalo brand canvas delete <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--yes` / `-y` |  |  | Do not ask for confirmation. |

##### `brand canvas export`

Export a canvas as JSON (to a file, or to the screen).

```text
kodalo brand canvas export <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--output` / `-o` | file |  | Write to a file. |

##### `brand canvas import`

Import a canvas from a JSON file made by `canvas export`.

```text
kodalo brand canvas import <file> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--name` | text |  | Name for the new canvas. |

### `settings`

Change Kodalo's settings. All of them are stored in the local database (secrets in the system keychain) and apply straight away.

#### `settings ai`

Connect Kodalo to Claude, ChatGPT or Gemini, and choose their models.

Providers: `claude_api` (Claude API), `claude_code` (the Claude Code program on this computer), `chatgpt_api` (ChatGPT API) and `gemini_api` (Gemini API). Several connections can be on at once, and one is the default. An API key is never an argument: `--key` asks for it at a hidden prompt (or reads it when piped) and it is kept in the system keychain, never in the database. Only the last four characters are shown afterwards. Claude Code uses your own sign-in and needs no key; `test` only checks that `claude` is installed.

##### `settings ai list`

List every provider with its connection, saved or not.

```text
kodalo settings ai list [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings ai show`

Show the connection to one provider.

```text
kodalo settings ai show <provider> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings ai set`

Save the connection to a provider. Values you leave out are kept.

```text
kodalo settings ai set <provider> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--key` |  |  | Enter the API key at a hidden prompt, or pipe it in. Never an argument. |
| `--enable` / `--disable` |  |  | Turn the connection on or off. |
| `--base-url` | text |  | Another address for the API. Empty for the default. |
| `--json` |  |  | Output as JSON. |

##### `settings ai test`

Check that the connection works. Exits with 1 when it does not.

```text
kodalo settings ai test <provider> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings ai default`

Make a provider the default connection.

```text
kodalo settings ai default <provider> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings ai remove`

Forget a connection: its settings, models and API key.

```text
kodalo settings ai remove <provider>
```

##### `settings ai history`

List the calls made to AI providers, newest first, or show one with --show <id>.

```text
kodalo settings ai history [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--period` | text | `all` | One of: day, week, month, year, all, custom. Default: all. |
| `--from` | text |  | With --period custom: the first day, 2026-11-01. |
| `--to` | text |  | With --period custom: the last day, 2026-11-30. |
| `--limit` | number | `50` | Entries to show (1 to 200). |
| `--offset` | number |  | Entries to skip. |
| `--show` | text |  | Show one entry, with its text if it was kept. |
| `--json` |  |  | Output as JSON. |

##### `settings ai usage`

Show the tokens used per connection and model, and per day.

```text
kodalo settings ai usage [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--period` | text | `all` | One of: day, week, month, year, all, custom. Default: all. |
| `--from` | text |  | With --period custom: the first day, 2026-11-01. |
| `--to` | text |  | With --period custom: the last day, 2026-11-30. |
| `--json` |  |  | Output as JSON. |

##### `settings ai history-settings`

Show or change how the AI history is kept. With no options, shows the current values.

```text
kodalo settings ai history-settings [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--store-text` / `--no-store-text` |  |  | Keep the text of prompts and answers (off by default). |
| `--retention-days` | number |  | Remove entries older than this many days (default 90; 0 keeps them forever). |
| `--json` |  |  | Output as JSON. |

##### `settings ai purge-history`

Remove every entry of the AI history. This cannot be undone.

```text
kodalo settings ai purge-history [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--yes` / `-y` |  |  | Do not ask for confirmation. |

##### `settings ai models`

Manage the models of a connection.

###### `settings ai models list`

List the saved models of a connection.

```text
kodalo settings ai models list <provider> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings ai models refresh`

Ask the provider which models it offers and save them.

```text
kodalo settings ai models refresh <provider> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings ai models set`

Add a model or change its settings. Options you leave out go back to the provider's own.

```text
kodalo settings ai models set <provider> <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--max-tokens` | number |  | Most tokens to generate, 1 to 1000000. |
| `--temperature` | number |  | Randomness, 0 to 2. |
| `--timeout` | number |  | Seconds to wait for an answer, 1 to 600. |
| `--json` |  |  | Output as JSON. |

###### `settings ai models default`

Make a model the one the connection uses by default.

```text
kodalo settings ai models default <provider> <name> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings ai models remove`

Forget a model. A model the provider offers comes back on the next refresh.

```text
kodalo settings ai models remove <provider> <name>
```

#### `settings github`

Choose how Kodalo reaches GitHub: a local folder, the gh CLI or the web.

Modes: `local_folder` (repositories already on this computer), `gh_cli` (the GitHub CLI, the default) or `web_fetch` (public repositories over the internet, no sign-in).

##### `settings github show`

Show the current GitHub connectivity setting.

```text
kodalo settings github show [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings github set`

Choose the way to reach GitHub.

```text
kodalo settings github set <mode> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--folder` | text |  | Folder holding your repositories (for local_folder). |
| `--manifest-limit` | number |  | How many project files (package.json ...) to read from GitHub, 1 to 100. |
| `--document-limit` | number |  | How many documents (the README and the docs it links to) to read, 1 to 50. |
| `--document-max-kb` | number |  | How much of each document to read, in KB, 1 to 2000. |
| `--json` |  |  | Output as JSON. |

##### `settings github check`

Check that the chosen way works. Exits with 1 when it does not.

```text
kodalo settings github check [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

#### `settings logs`

Choose the log level and how long log files are kept.

Kodalo writes a plain-text log, one file per day (`kodalo-YYYY-MM-DD.log`), to the `logs` folder of the data folder. The command line, the API and the window share it. The level is `INFO` by default and files are kept 90 days.

##### `settings logs show`

Show the log level, retention and the folder the logs are written to.

```text
kodalo settings logs show [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings logs set`

Change the log level and/or how many days of logs are kept.

```text
kodalo settings logs set [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--level` | text |  | One of: DEBUG, INFO, WARNING, ERROR, CRITICAL. Default: INFO. |
| `--retention` | number |  | Days to keep log files, 1 to 3650. Default: 90. |
| `--json` |  |  | Output as JSON. |

#### `settings platforms`

Choose how many hashtags a post gets, and the ones every post carries.

`<platform>` is `instagram`.

##### `settings platforms show`

Show a platform's hashtag settings.

```text
kodalo settings platforms show <platform> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

##### `settings platforms set`

Change a platform's settings. What you leave out stays as it is.

```text
kodalo settings platforms set <platform> [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--hashtags` | number |  | Hashtags on each post, the default ones included, 0 to 30. |
| `--default-hashtags` | text |  | Hashtags every post carries, separated by spaces, for example "#sweepito". Use an empty value to remove them. |
| `--use-social-preview` / `--no-social-preview` |  |  | The designer may use the social preview. |
| `--use-repo-icon` / `--no-repo-icon` |  |  | The designer may use the repository icon. |
| `--use-icons` / `--no-icons` |  |  | The designer may use icons. |
| `--build-custom-images` / `--no-custom-images` |  |  | The designer may build custom images as needed. |
| `--use-ai-templates` / `--no-ai-templates` |  |  | The AI writes the HTML and CSS of each slide instead of the fixed templates. |
| `--json` |  |  | Output as JSON. |

##### `settings platforms instagram`

Connect Kodalo to Instagram with an access token.

Posting needs a token and account ID from the Meta dashboard, and cloudflared for the temporary public address Instagram fetches the pictures from.

###### `settings platforms instagram status`

Show the connected Instagram account. Does not contact Instagram.

```text
kodalo settings platforms instagram status [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings platforms instagram connect`

Connect Instagram. The access token is asked for at a hidden prompt, or piped in, and
never taken as an argument. It is checked with Meta and kept in the system keychain.

```text
kodalo settings platforms instagram connect [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings platforms instagram check`

Ask Instagram whether the saved token still works.

```text
kodalo settings platforms instagram check [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings platforms instagram disconnect`

Remove the token from the keychain and forget the account.

```text
kodalo settings platforms instagram disconnect
```

###### `settings platforms instagram tunnel`

Check or install cloudflared, the tool posting to Instagram needs.

###### `settings platforms instagram tunnel status`

Show whether cloudflared, which posting needs, is installed. Installs nothing.

```text
kodalo settings platforms instagram tunnel status [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

###### `settings platforms instagram tunnel install`

Install cloudflared (a third-party tool from Cloudflare) when it is missing.

```text
kodalo settings platforms instagram tunnel install [options]
```

| Option | Value | Default | Description |
| --- | --- | --- | --- |
| `--json` |  |  | Output as JSON. |

```console
$ kodalo brand create Main --palette paper
$ kodalo brand logo set Main logo.svg
$ kodalo brand check Main --strict
```

## Output conventions

- Results go to **stdout**, so they can be piped.
- Errors and extra detail go to **stderr**.
- `--json` prints a single JSON document to stdout, even with `--quiet`.
- Color is turned off automatically when output is piped, when `NO_COLOR` is set, or with `--no-color`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | The command failed, for example an unknown brand, a name already in use, an invalid value, a failed `brand check --strict`, or an unexpected error. |
| `2` | Invalid usage, such as an unknown option or conflicting options. |

## Errors

Expected failures print `Error: <message>` to stderr and exit with code 1. Unexpected exceptions are caught by `run()` in `src/kodalo/cli/cli.py`: they print a one-line message and a hint to stderr, and show a traceback only with `--verbose`. Local variables are never shown, because they can contain secrets.

## Adding a command

1. Add the logic to `kodalo.core` as a plain function that returns a value or raises an exception. It must not print or exit.
2. Add a command under `src/kodalo/cli/` that calls it, writes through the consoles in `output.py`, and raises `typer.Exit(code=1)` on failure.
3. Add a `--json` option if the command returns data.
4. Add tests with `typer.testing.CliRunner` and document the command in this file, with its arguments and options.
