# Packaging

How the installers are built. For publishing them, see [releasing](releasing.md).

## What is built

| Product | Contents | Windows |
| --- | --- | --- |
| CLI | `kodalo` | `kodalo-cli-<version>.setup.exe`, and a portable `…-windows-x64.zip` |
| UI | `kodalo-ui` (window) | `kodalo-<version>.setup.exe` |

Only Windows gets an installer. Elsewhere, install the PyPI package.

## The pieces

```text
installer/pyinstaller/       cli.spec, ui.spec, common.py   freeze the programs (Windows only)
installer/projectinfo.py       names, version and title read from pyproject.toml and the code
installer/windows/nsis/      cli.nsi, ui.nsi, common.nsh, path.ps1   Windows setup.exe files
installer/tools.toml         pinned version of NSIS
scripts/build_installer.py   runs the steps above
scripts/update_manifests.py  release notes and the Scoop manifest
```

Names, version, icon and description are never repeated: executable names are the `[project.scripts]` keys, the version is `__version__`, the title is `TITLE` in `kodalo_ui/app.py`, the icon is the `.ico` in `brand/light`, and the rest comes from `[project]`. Each of these is defined once and read by the installer files through `installer/projectinfo.py`, which takes the command and window names from `[project.scripts]` and `[tool.installer]` in `pyproject.toml`. Renaming the project (the Init workflow does it) therefore needs no edit in the installer files.

## Building locally

```bash
uv sync --group installer
uv run python scripts/build_installer.py            # everything this OS can build
uv run python scripts/build_installer.py cli        # only the command line
uv run python scripts/build_installer.py ui --build-frontend --smoke
```

Results are in `dist/installer/`; the PyInstaller folders are in `build/installer/`. `--smoke` starts each built program and checks it answers. Independent steps (the CLI and UI PyInstaller builds, then the setups and zip, or the deb and rpm) run side by side on as many threads as there are CPUs; `--jobs 1` runs them one after the other, which keeps the log in order when you are chasing a failure.

| You need | For |
| --- | --- |
| `uv sync --group installer` | PyInstaller and the build backend |
| Node (see `.nvmrc`) | the frontend, for the UI (`--build-frontend` runs `npm ci` and `npm run build`) |
| NSIS (version in `installer/tools.toml`) | Windows setups; `makensis` on `PATH` or in `Program Files (x86)\NSIS` |

## PyInstaller

Both specs make one-folder builds (no one-file build), with an executable per program and one shared `lib/`.

- `cli.spec` builds `kodalo` alone, on any OS, with none of the window's libraries (about 37 MB).
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

Silent use, for scripts and for winget:

```text
kodalo-cli-<version>.setup.exe /S [/allusers | /currentuser] [/NOPATH] [/D=C:\folder]
kodalo-<version>.setup.exe     /S [/allusers | /currentuser] [/DESKTOP] [/D=C:\folder]
uninstall.exe /S [/PURGE]
```

`/D=` must come last. `/PURGE` also removes the data folder, if one is configured (`USER_DATA_DIR`; none is set by default, because the data location depends on your app).

Each product has a GUID in its `.nsi` file. It identifies the product for upgrades, so keep it for the life of the project. Init generates new ones for you; to make one by hand, use `python -c "import uuid; print(uuid.uuid4())"`.

## WebView2

The window uses the Microsoft Edge WebView2 runtime, which is already part of Windows 10 and 11. The installers do not add it. On an older machine the runtime can be downloaded from [Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/), and `cornea doctor` checks for it.

## Checks

- `tests/cli/integration/test_frozen_cli.py` and `tests/ui/integration/test_frozen_ui.py` start the built programs (the window without a window) and check they answer.
- `build.yml` runs on pull requests that touch the installers. It builds on Windows, installs each setup, runs the program and uninstalls it. It is not part of the required `ci` check.

Windows may refuse to start a freshly built, unsigned program (Smart App Control or application control returns error 4551). The smoke tests skip in that case. Signing removes the problem (see [releasing](releasing.md)).

The database migration scripts are frozen into the executable like the rest of the code, not installed as files (`kodalo/core/storage/bundled.py` hands them to Alembic).
