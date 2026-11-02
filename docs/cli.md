# CLI reference

`kodalo` is a command line tool built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/). Rename the command and replace the example commands below with your own.

## Running

```bash
kodalo --help          # installed script
python -m kodalo.cli       # without relying on the script being on PATH
uvx --from Kodalo kodalo --help   # one-off, no install
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

The full, generated list of commands and options is in [cli-reference.md](cli-reference.md). Regenerate it after changing a command:

```bash
uv run typer kodalo.cli.cli utils docs --name kodalo --output docs/cli-reference.md
```

CI fails if the file is out of date.

## Commands

### `doctor`

Check the installation and the local data without changing anything: the Kodalo and Python versions, the platform, the required libraries, the data folder, the database (its version, or that it is not created yet), the number of brand profiles and the fonts available. Each line is `ok`, `warn` (optional) or `FAIL` (required). Exits with 1 if a required check fails, for example a database written by a newer Kodalo. Add `--json` for `{"healthy": ..., "checks": [...]}`.

### `settings github`

Choose how Kodalo reaches GitHub: `local_folder` (repositories already on this computer), `gh_cli` (the GitHub CLI, the default) or `web_fetch` (public repositories over the internet, no sign-in). The choice is stored in the local database.

| Command | What it does |
| --- | --- |
| `settings github show` | Show the current mode and folder. `--json` for machine-readable output. |
| `settings github set <mode>` | Choose the mode. `--folder PATH` sets the folder (required the first time for `local_folder`). |
| `settings github check` | Try the chosen way once. Exits with 1 when it does not work. |

### `studio`

Start a post from a repository. Reading follows the GitHub mode: `gh_cli` and `web_fetch` read a GitHub address (`https://github.com/owner/repo` or `owner/repo`); `local_folder` reads a folder with git and its files. What is read (metadata, languages, top-level structure, warnings) is stored in the local database.

| Command | What it does |
| --- | --- |
| `studio source <value>` | Check the folder or address against the mode. `--json` for machine-readable output. Exits with 1 when it is not valid. |
| `studio read <value>` | Read the repository and store it. A stored repository is returned as is; `--refresh` reads again. For a folder the first read needs `--owner`, `--repo`, `--license` and `--branch`; `--description`, `--homepage`, `--topic` (repeatable), `--private`, `--fork` and `--archived` are optional. `--json` for machine-readable output. |
| `studio list` | List stored repositories. `--json` for machine-readable output. |
| `studio show <id>` | Show one stored repository. `--json` for machine-readable output. |

### `brand`

Manage brand profiles. Every command takes the profile by name (any case) or by id. Messages go to stderr and `--quiet` hides them; data goes to stdout.

| Command | What it does |
| --- | --- |
| `brand list` | List profiles. `--json` for machine-readable output. |
| `brand show NAME` | Show a profile in groups (General, Colors with a swatch of each color, Fonts, Logo, Layout). `--json` prints the full profile. |
| `brand create NAME` | Create a profile from a palette: `--palette NAME` (default `Midnight`; see `brand palette list`). `--default` makes it the default. The first profile is always the default. |
| `brand rename NAME NEW_NAME` | Rename a profile. Names are unique, ignoring case. Renaming to the same name is an error; changing only the case is allowed. |
| `brand duplicate NAME NEW_NAME` | Copy a profile, including its logo files. |
| `brand default NAME` | Make a profile the default. |
| `brand delete NAME` | Delete a profile and its logo files after asking; `--yes` skips the question. Deleting the default promotes another profile. |
| `brand settings set NAME PATH VALUE` | Change one setting, for example `brand settings set Main colors.primary.light '#2563eb'`. Choose a layout with `brand settings set Main layout_id "Compact"` (a name or an id). The value is checked like any other brand data. |
| `brand settings list NAME` | List the settings that `settings set` accepts, with their values. `--json` for machine-readable output. |
| `brand check NAME` | Report the contrast of text and accent colors in light and dark mode. `--strict` exits with 1 if any check fails; `--json` for machine-readable output. |
| `brand palette list` / `show NAME` | List palettes (built-in first) or show one with a swatch of each color. `--json` for machine-readable output. |
| `brand palette add NAME` | Create a palette from a brand's colors (`--from-brand`) or another palette (`--from-palette`, default Midnight). |
| `brand palette set NAME PATH VALUE` | Change one color of a palette of your own, for example `brand palette set Ocean primary.light '#2563eb'`. |
| `brand palette rename`, `duplicate`, `delete` | Rename, copy or delete a palette. Built-in palettes can be copied but not changed. Brands made from a palette keep their colors. |
| `brand palette export NAME` / `import FILE` | Write a palette as JSON to stdout or a file (`--output`); add one from a file (`--name`). |
| `brand fonts` | List the font catalogue with each font's category and source: bundled fonts plus installed ones (`--bundled` for only the bundled list). |
| `brand export NAME` | Write the profile and its logos as JSON to stdout, or to a file with `--output`. |
| `brand import FILE` | Add a profile from an exported file. `--name` sets its name; a name already in use gets a number added. |
| `brand canvas list` | List canvases (built-in first) and the layouts that use each. `--json` for machine-readable output. |
| `brand canvas show NAME` | Show one canvas by name or id. `--json` prints it in full. |
| `brand canvas add NAME WIDTH HEIGHT` | Create a canvas; sizes are 200 to 4000 pixels. |
| `brand canvas edit NAME` | Rename or resize with `--name`, `--width`, `--height`. Every layout, and so every brand, using it follows. Built-in canvases cannot be changed. |
| `brand canvas duplicate NAME NEW_NAME` | Copy a canvas, built in or not, as a canvas of your own. |
| `brand canvas delete NAME` | Delete a canvas no layout uses, after asking; `--yes` skips the question. |
| `brand canvas export NAME` / `import FILE` | Write a canvas as JSON to stdout or a file (`--output`); add one from a file (`--name`). |
| `brand layout list` / `show NAME` / `settings NAME` | List layouts (built-in first, with canvas, slide count and the brands using each), show one, or list its settings. |
| `brand layout add NAME` | Create a layout from another one (`--from-layout`, default Default); change it with `layout set`. |
| `brand layout set NAME PATH VALUE` | Change one setting of a layout of your own, for example `slides_count 8` or `canvas_id "Instagram story"`. Brands using it follow. |
| `brand layout rename`, `duplicate`, `delete` | Rename, copy or delete a layout. Built-in layouts (Default, Compact, Spacious) can be copied but not changed; a layout a brand uses cannot be deleted. |
| `brand layout export NAME` / `import FILE` | Write a layout, with its canvas, as JSON to stdout or a file (`--output`); add one from a file (`--name`). |
| `brand logo set NAME FILE` | Set the logo from a PNG or SVG file (up to 2 MB). `--dark` sets the dark-mode logo. SVG files with scripts or external links are refused. |
| `brand logo remove NAME` | Remove the logo (`--dark` for the dark-mode one). |

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
| `1` | The command failed, for example an unknown brand, a name already in use, an invalid value, or a failed `brand check --strict`; or an unexpected error. |
| `2` | Invalid usage, such as an unknown option or conflicting options. |

## Errors

Expected failures print `Error: <message>` to stderr and exit with code 1. Unexpected exceptions are caught by `run()` in `cli.py`: they print a one-line message and a hint to stderr, and show a traceback only with `--verbose`. Local variables are never shown, because they can contain secrets.

## Adding a command

1. Add the logic to `kodalo_package` as a plain function that returns a value or raises an exception. It must not print or exit.
2. Add a command to `src/kodalo_cli/cli.py` that calls it, writes through the consoles in `output.py`, and raises `typer.Exit(code=1)` on failure.
3. Add a `--json` option if the command returns data.
4. Add tests with `typer.testing.CliRunner`, document the command in this file, and regenerate `cli-reference.md`.
