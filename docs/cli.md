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
| `settings github show` | Show the current mode, folder, number of project files to read and the document limits. `--refresh-with-ai` asks the default AI model for parser configs for project files no config covers: it prints the files and the expected tokens and asks first (`--yes` skips the question), then reads again with the new configs. `--json` for machine-readable output. |
| `settings github set <mode>` | Choose the mode. `--folder PATH` sets the folder (required the first time for `local_folder`). `--manifest-limit N` sets how many project files (`package.json`, `pyproject.toml` ...) are read from GitHub, 1 to 100 (default 10). `--document-limit N` sets how many documents (the README and the docs it links to) are read for `repositories add --readme`, 1 to 50 (default 10). `--document-max-kb N` sets how much of each document is read, 1 to 2000 KB (default 200). |
| `settings github check` | Try the chosen way once. Exits with 1 when it does not work. |

### `settings logs`

Kodalo writes a plain-text log, one file per day (`kodalo-YYYY-MM-DD.log`), to the `logs` folder of the data folder. The command line, the API and the window share it. The level (`INFO` by default) and how many days files are kept (90 by default) are stored in the local database and apply straight away.

| Command | What it does |
| --- | --- |
| `settings logs show` | Show the level, the retention and the log folder. `--json` for machine-readable output. |
| `settings logs set` | `--level` is one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. `--retention N` keeps log files for N days, 1 to 3650. |

### `settings platforms`

| Command | What it does |
| --- | --- |
| `settings platforms show <platform>` | Show how many hashtags a post for that platform gets (`hashtags per post`) and the default hashtags every post carries. `<platform>` is `instagram`. `--json` for machine-readable output. |
| `settings platforms set <platform>` | `--hashtags N` sets the number of hashtags on each post, the default ones included, 0 to 30 (default 5). `--default-hashtags "#a #b"` sets the hashtags every post carries before the ones the AI writes; an empty value removes them. `--use-social-preview/--no-social-preview`, `--use-repo-icon/--no-repo-icon`, `--use-icons/--no-icons` and `--build-custom-images/--no-custom-images` choose which visuals the designer may use, and `--use-ai-templates/--no-ai-templates` lets the AI write the HTML and CSS of each slide instead of the fixed templates (all off until chosen). What is left out stays as it is. Exits with 1 when the number is out of range or there are more default hashtags than hashtags. |
| `settings platforms instagram connect` | Connect Instagram. Asks for the Instagram account ID, then the access token at a hidden prompt (or reads both from a pipe), checks them with Meta and keeps the token in the system keychain. `--json` for machine-readable output. Exits with 1 when the token or account ID is malformed, refused or the keychain is unavailable. |
| `settings platforms instagram status` | Show the connected account (name, ID, type, last four characters of the token, when it was connected). Does not contact Instagram. `--json` for machine-readable output. |
| `settings platforms instagram check` | Ask Instagram whether the saved token still works. Exits with 1 when not connected or the token no longer works. `--json` for machine-readable output. |
| `settings platforms instagram tunnel status` | Show whether cloudflared, the third-party tool posting needs, is installed. Installs nothing. `--json` for machine-readable output. |
| `settings platforms instagram tunnel install` | Install cloudflared when it is missing (winget, else a checked download). Exits with 1 when it cannot be installed. `--json` for machine-readable output. |
| `settings platforms instagram disconnect` | Remove the token from the keychain and forget the account. |

### `settings ai`

Connect Kodalo to an AI provider: `claude_api` (Claude API), `claude_code` (the Claude Code program on this computer), `chatgpt_api` (ChatGPT API) or `gemini_api` (Gemini API). Several connections can be on at once, and one is the default. An API key is never an argument: `--key` asks for it at a hidden prompt (or reads it when piped), and it is kept in the system keychain (Windows Credential Manager), never in the database. Only the last four characters are shown afterwards. Claude Code uses your own sign-in and needs no key; `test` only checks that `claude` is installed.

| Command | What it does |
| --- | --- |
| `settings ai list` | Every provider with its state, key, status and default model. `--json` for machine-readable output. |
| `settings ai show <provider>` | One connection in detail. |
| `settings ai set <provider>` | Save a connection. `--key` enters the API key, `--enable` / `--disable` turns it on or off, `--base-url URL` uses another address (empty for the default). Anything left out is kept. |
| `settings ai test <provider>` | Check the connection. Exits with 1 when it does not work. |
| `settings ai default <provider>` | Make a saved, enabled connection the default. |
| `settings ai remove <provider>` | Forget a connection: settings, models and key. |
| `settings ai history` | The calls made to AI providers, newest first: `--period day\|week\|month\|year\|all\|custom` (with `--from` and `--to` dates `2026-11-01`), `--limit`, `--offset`; `--show <id>` shows one entry with its text when it was kept. `--json` for machine-readable output. |
| `settings ai usage` | Calls and tokens per connection and model, and per day, with the same `--period`, `--from` and `--to`. `--json` is available. |
| `settings ai history-settings` | Show or change how history is kept: `--store-text` / `--no-store-text` (the text of prompts and answers, off by default) and `--retention-days N` (default 90; 0 keeps entries forever). |
| `settings ai purge-history` | Remove the whole history after a confirmation (`--yes` skips it). |
| `settings ai models list <provider>` | The saved models and their settings. |
| `settings ai models refresh <provider>` | Ask the provider for its models and save them. Models you added by hand are kept. |
| `settings ai models set <provider> <name>` | Add a model or change it: `--max-tokens` (1 to 1000000), `--temperature` (0 to 2), `--timeout` seconds (1 to 600). A new model starts with Kodalo's standard settings for its kind (opus, sonnet, haiku, gemini, gpt, or the app-wide ones) wherever an option is left out; for a saved model, options left out go back to the provider's own default. Refreshing gives new models the same standard settings and keeps the ones you changed. |
| `settings ai models default <provider> <name>` | Choose the model the connection uses by default. |
| `settings ai models remove <provider> <name>` | Forget a model (one the provider offers comes back on the next refresh). |

### `repositories`

| Command | What it does |
| --- | --- |
| `repositories check <value>` | Check the folder or address against the mode. `--json` for machine-readable output. Exits with 1 when it is not valid. |
| `repositories add <value>` | Add a repository: read it and keep it, with its notable folders, project files (package, version and dependencies; see [manifest-parsers.md](manifest-parsers.md), where you can also add your own file types) and whether it is a monorepo. It also shows the documentation files found (README, changelog, contributing, license, docs folder) and the files that were not read, with the reason. It also lists the frameworks and tooling in use with their evidence (see [framework-detection.md](framework-detection.md)); `--refresh-with-ai` also asks the default AI model about packages no config knows, in the same single question as the project files. An added repository is returned as is; `--refresh` reads again. For a folder the first read needs `--owner`, `--repo`, `--license` and `--branch`; `--description`, `--homepage`, `--topic` (repeatable), `--private`, `--fork` and `--archived` are optional. `--readme` also reads the README and the docs it links to without AI and shows the purpose, installation methods, capabilities and the documents read or skipped (see [readme-analysis.md](readme-analysis.md)); the result is kept, and `--refresh` reads it again. `--readme-with-ai` (which implies `--readme`) asks the default AI model to read those same documents and write the purpose, installation methods, capabilities and use cases, after printing the documents it would send and the expected tokens and asking first (`--yes` skips the question); see [readme-analysis.md](readme-analysis.md). With `--readme`, `--json` prints `{"repository": ..., "readme": ...}`. `--json` for machine-readable output. |
| `repositories list` | List the added repositories with their ids. `--json` for machine-readable output. |
| `repositories show <id>` | Show one added repository. `--json` for machine-readable output. |
| `repositories remove <id>` | Remove a repository and everything saved about it. Asks first; `--yes` skips the question. |

### `studio`

Make a post from an added repository, step by step: ideas, then copy, then design. Checking, reading and analyzing a repository is done with `repositories`. Every step takes the repository id, and the steps after ideas also take the brand (`--brand`, name or id; its canvas must be for Instagram) and the idea (`--idea`, e.g. `idea-1`; `--hook` picks another hook). A tool post is the default; for a feature post add `--type feature`, `--kind` (`features`, `use_cases` or `capabilities`) and `--name`. Commands that ask the AI print what would be sent and the expected tokens, then ask first; `--yes` skips the question. `--json` prints machine-readable output. A command that shows something saved exits with 1 when nothing was made yet.

| Command | What it does |
| --- | --- |
| `studio ideas plan <id>` | Say what the AI would be sent for the ideas and what it costs. Nothing is sent. |
| `studio ideas make <id>` | Ask the default AI model for a strategy, three angles with hooks and the number of post ideas set in Settings (5 by default). New ideas are added to the ones saved before; ones already made are skipped. |
| `studio ideas show <id>` | Show the saved ideas. |
| `studio copy plan <id>` | Say what the AI would be sent for the copy. Nothing is sent. |
| `studio copy make <id>` | Write the slides, caption, alternative opening and hashtags of an idea with the AI. Replaces the copy saved before. |
| `studio copy show <id>` | Show the saved copy. |
| `studio copy edit <id> --file <json>` | Replace the saved copy with your edit. The file has the shape of `studio copy show --json`; the limits are applied. |
| `studio design plan <id>` | Say what the AI would be sent to design the saved copy. Nothing is sent. |
| `studio design make <id>` | Ask the AI how to lay out each slide. Replaces the design saved before. |
| `studio design show <id>` | Show the saved design. |
| `studio design export <id> --folder PATH` | Make a picture of every slide and write them, with a `caption.txt`, into a new subfolder of an existing `--folder`, to post by hand; `--mode light\|dark`, `--json`. Sends nothing to Instagram. Needs Microsoft Edge. Exits with 1 when the folder does not exist or nothing was designed. |
| `studio design slide <id> --slide N` | Export one slide (a fixed template's or the AI's layout) as a self-contained HTML page; `--mode light\|dark`, `--output` writes a file instead of stdout. |
| `studio design svg <id> --slide N` | Export the drawing the AI made for one slide as SVG; `--output` writes a file. |

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
