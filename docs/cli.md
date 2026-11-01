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

### `brand`

Manage brand profiles. Every command takes the profile by name (any case) or by id. Messages go to stderr and `--quiet` hides them; data goes to stdout.

| Command | What it does |
| --- | --- |
| `brand list` | List profiles. `--json` for machine-readable output. |
| `brand show NAME` | Show every setting of a profile. `--json` prints the full profile. |
| `brand create NAME` | Create a profile from a starter palette: `--palette midnight\|paper\|graphite` (default `midnight`). `--default` makes it the default. The first profile is always the default. |
| `brand rename NAME NEW_NAME` | Rename a profile. Names are unique, ignoring case. |
| `brand duplicate NAME NEW_NAME` | Copy a profile, including its logo files. |
| `brand default NAME` | Make a profile the default. |
| `brand delete NAME` | Delete a profile and its logo files after asking; `--yes` skips the question. Deleting the default promotes another profile. |
| `brand set NAME PATH VALUE` | Change one setting, for example `brand set Main colors.primary.light '#2563eb'` or `brand set Main layout.align center`. The value is checked like any other brand data. |
| `brand settings NAME` | List the paths that `set` accepts. |
| `brand check NAME` | Report the contrast of text and accent colors in light and dark mode. `--strict` exits with 1 if any check fails; `--json` for machine-readable output. |
| `brand palettes` | List the starter palettes. |
| `brand fonts` | List the fonts a profile can use: bundled fonts plus installed ones (`--bundled` for only the bundled list). |
| `brand export NAME` | Write the profile and its logos as JSON to stdout, or to a file with `--output`. |
| `brand import FILE` | Add a profile from an exported file. `--name` sets its name; a name already in use gets a number added. |
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
