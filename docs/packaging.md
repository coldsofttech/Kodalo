# Packaging and releasing

How the installers are built and how a release reaches users. Kodalo is released as Windows installers on a GitHub release; nothing is published to PyPI or a package manager, and the installers are not signed.

- [What is built](#what-is-built)
- [Building locally](#building-locally)
- [Releasing](#releasing)

## What is built

| Product | Contents | Windows |
| --- | --- | --- |
| CLI | `kodalo` | `kodalo-cli-<version>.setup.exe`, and a portable `…-windows-x64.zip` |
| UI | `kodalo-ui` (window) | `kodalo-<version>.setup.exe` |

Only Windows gets an installer.

## The pieces

```text
installer/pyinstaller/       cli.spec, ui.spec, common.py   freeze the programs
installer/projectinfo.py       names, version and title read from pyproject.toml and the code
installer/windows/nsis/      cli.nsi, ui.nsi, common.nsh, path.ps1   Windows setup.exe files
installer/tools.toml         pinned version of NSIS
scripts/build_installer.py   runs the steps above
scripts/update_manifests.py  release notes for a release
```

Names, version, icon and description are never repeated: executable names are the `[project.scripts]` keys, the version is `__version__`, the title is `TITLE` in `src/kodalo/ui/app.py`, the icon is the `.ico` in `brand/light`, and the rest comes from `[project]`. Each of these is defined once and read by the installer files through `installer/projectinfo.py`, which takes the command and window names from `[project.scripts]` and `[tool.installer]` in `pyproject.toml`. The installer files therefore never name the project.

## Building locally

```bash
uv sync --group installer
uv run python scripts/build_installer.py            # everything this OS can build
uv run python scripts/build_installer.py cli        # only the command line
uv run python scripts/build_installer.py ui --build-frontend --smoke
```

Results are in `dist/installer/`; the PyInstaller folders are in `build/installer/`. `--smoke` starts each built program and checks it answers. Independent steps (the CLI and UI PyInstaller builds, then the setups and zip) run side by side on as many threads as there are CPUs; `--jobs 1` runs them one after the other, which keeps the log in order when you are chasing a failure.

| You need | For |
| --- | --- |
| `uv sync --group installer` | PyInstaller and the build backend |
| Node (version in `src/kodalo/ui/ui/.nvmrc`) | the frontend, for the UI (`--build-frontend` runs `npm ci` and `npm run build`) |
| NSIS (version in `installer/tools.toml`) | Windows setups; `makensis` on `PATH` or in `Program Files (x86)\NSIS` |

## PyInstaller

Both specs make one-folder builds (no one-file build), with an executable per program and one shared `lib/`.

- `cli.spec` builds `kodalo` alone, on any OS, with none of the window's libraries.
- `ui.spec` (Windows only) builds `kodalo-ui` alone. The window has no console, and the built frontend is frozen into `lib/`.
- `common.py` holds what they share. The entry scripts are generated from the `[project.scripts]` targets.

The Windows executables carry the icon and file properties (name, version, description), also taken from the project.

## Windows setup (NSIS)

`common.nsh` holds the behavior and `cli.nsi` and `ui.nsi` set what differs. Settings arrive as `/D` flags from `build_installer.py`.

- **Who it is for:** the default is a per-user install (`%LOCALAPPDATA%\Programs\<publisher>\<name>\CLI` or `\UI`, so the two products never share files). The mode page offers all users (`Program Files`), which asks for administrator rights. An administrator sees one prompt at start.
- **License:** a license page shows the `LICENSE` file when it is passed in.
- **Start Menu:** The `<name>` folder under Programs holds one shortcut (no uninstall shortcut; uninstall from Settings > Apps). The CLI's shortcut opens a prompt where `kodalo` works. The UI setup also offers a desktop shortcut.
- **PATH (CLI only):** a component, on by default, edits the registry through `path.ps1` and is removed again on uninstall. The UI setup never touches PATH.
- **Uninstall:** removes only what setup installed, so a folder chosen by hand keeps anything else in it. Settings and data stay unless the user opts in.
- **Upgrades:** a newer setup with the same GUID replaces the old install and clears the old `lib/` first.

Silent use, for scripts:

```text
kodalo-cli-<version>.setup.exe /S [/allusers | /currentuser] [/NOPATH] [/D=C:\folder]
kodalo-<version>.setup.exe     /S [/allusers | /currentuser] [/DESKTOP] [/D=C:\folder]
uninstall.exe /S [/PURGE]
```

`/D=` must come last. `/PURGE` also removes a data folder when the build passes one (`USER_DATA_DIR`). Kodalo's own data (`%LOCALAPPDATA%\Kodalo`) is not configured that way today, so uninstalling never removes it.

Each product has a GUID in its `.nsi` file. It identifies the product for upgrades, so keep it for the life of the project. To make a new one, use `python -c "import uuid; print(uuid.uuid4())"`.

## WebView2

The window uses the Microsoft Edge WebView2 runtime, which is already part of Windows 10 and 11. The installers do not add it. On an older machine the runtime can be downloaded from [Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/). Exporting a designed post to pictures (`studio design export`) also needs Microsoft Edge.

## Checks

- `tests/cli/integration/test_frozen_cli.py` and `tests/ui/integration/test_frozen_ui.py` start the built programs (the window without a window) and check they answer.
- `build.yml` runs on pull requests that touch the installers. It builds on Windows, installs each setup, runs the program and uninstalls it. It is not part of the required `ci` check.

Windows may refuse to start a freshly built, unsigned program (Smart App Control or application control returns error 4551), and SmartScreen can warn when someone runs a downloaded setup. The smoke tests skip in the first case.

The database migration scripts are frozen into the executable like the rest of the code, not installed as files (`kodalo/core/storage/bundled.py` hands them to Alembic).

## Releasing

1. Bump `__version__` in `src/kodalo/__init__.py`, and move the `[Unreleased]` entries in `CHANGELOG.md` under a `## [x.y.z]` heading.
2. Merge that pull request, then publish a GitHub release tagged `v<version>`.
3. `release.yml` does the rest:

| Step | Result |
| --- | --- |
| Check | the tag must equal the version |
| Installers | the Windows setups and the portable zip, built and smoke-tested (30-minute timeout, under 10 minutes expected) |
| Release page | all files plus `SHA256SUMS.txt`; release notes from the `CHANGELOG.md` section, only if the release has no notes yet |

To check a download, run `Get-FileHash <file>` on Windows and compare with `SHA256SUMS.txt`.

### Installing

Download `kodalo-cli-<version>.setup.exe` (command line) or `kodalo-<version>.setup.exe` (window) from the release page and run it. Remove either from Settings > Apps. The switches for silent installs are in [Windows setup](#windows-setup-nsis).
