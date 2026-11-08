# Third-party notices

Kodalo is released under the [MIT License](../LICENSE). It is built on the open source components
listed below. Each component stays under its own license,
and the copyright belongs to its authors.

Versions are those pinned in `uv.lock` and `package-lock.json` at the time of writing. Each
package's own license file, shipped in its distribution, is the authoritative text.

- [Python packages in the command line and library](#python-packages-in-the-command-line-and-library)
- [Python packages in the window and API](#python-packages-in-the-window-and-api)
- [Frontend packages](#frontend-packages)
- [Build and installer tools](#build-and-installer-tools)

## Python packages in the command line and library

Installed with `pip install kodalo` and included in every installer.

| Package | Version | License | Project |
|---|---|---|---|
| Alembic | 1.20.1 | MIT | <https://github.com/sqlalchemy/alembic> |
| keyring | 25.7.0 | MIT | <https://github.com/jaraco/keyring> |
| Pillow | 13.0.0 | MIT-CMU (HPND) | <https://github.com/python-pillow/Pillow> |
| Pydantic | 2.14.2 | MIT | <https://github.com/pydantic/pydantic> |
| Rich | 15.0.0 | MIT | <https://github.com/Textualize/rich> |
| SQLAlchemy | 2.1.6 | MIT | <https://github.com/sqlalchemy/sqlalchemy> |
| Typer | 0.27.3 | MIT | <https://github.com/fastapi/typer> |

## Python packages in the window and API

Included only in the Windows window (the `api` and `ui` dependency groups). They are not part of
the published wheel.

| Package | Version | License | Project |
|---|---|---|---|
| FastAPI | 0.162.0 | MIT | <https://github.com/fastapi/fastapi> |
| Starlette | 1.10.0 | BSD-3-Clause | <https://github.com/encode/starlette> |
| uvicorn | 0.54.0 | BSD-3-Clause | <https://github.com/encode/uvicorn> |
| Cornea Shell | 0.1.0 | MIT | <https://github.com/coldsofttech/CorneaShell> |
| pywebview | 6.2.1 | BSD-3-Clause | <https://github.com/r0x0r/pywebview> |

Each of these packages brings its own dependencies. See `uv.lock` for the full list.

## Frontend packages

Bundled into the window's user interface.

| Package | Version | License | Project |
|---|---|---|---|
| React | 19.3.1 | MIT | <https://github.com/facebook/react> |
| React DOM | 19.3.1 | MIT | <https://github.com/facebook/react> |
| Bootstrap Icons | 1.13.2 | MIT | <https://github.com/twbs/icons> |
| Fluent UI Web Components | 2.6.1 | MIT | <https://github.com/microsoft/fluentui> |
| FAST (colors, element, foundation, web-utilities) | 5.3.1 / 1.14.0 / 2.50.0 / 5.4.1 | MIT | <https://github.com/Microsoft/fast> |
| scheduler | 0.28.0 | MIT | <https://github.com/facebook/react> |
| tabbable | 5.3.3 | MIT | <https://github.com/focus-trap/tabbable> |
| exenv-es6 | 1.1.1 | MIT | <https://github.com/chrisdholt/exenv-es6> |
| tslib | 1.14.1, 2.9.1 | 0BSD | <https://github.com/Microsoft/tslib> |

Development tools (Vite, Vitest, ESLint, Prettier and others) are not shipped and are not listed.

## Python dependencies of the packages above

Resolved from the project environment. Licenses are as declared in each package's metadata.

| Package | Version | License |
|---|---|---|
| annotated-doc, annotated-types, anyio, pydantic-core, typing-inspection | see `uv.lock` | MIT |
| bottle, proxy_tools, pythonnet, clr_loader | see `uv.lock` | MIT (clr_loader declares none; its project is MIT) |
| cffi | 2.1.1 | MIT-0 |
| pycparser, click, MarkupSafe, websockets | see `uv.lock` | BSD-3-Clause |
| colorama | 0.4.6 | BSD-3-Clause |
| h11, jaraco.classes, jaraco.context, jaraco.functools, more-itertools, Mako, markdown-it-py, mdurl | see `uv.lock` | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| pywin32-ctypes | 0.2.3 | BSD-3-Clause |
| shellingham | 1.5.4 | ISC |
| importlib_metadata, zipp | see `uv.lock` | Apache-2.0 (importlib_metadata), MIT (zipp) |
| typing_extensions | 4.16.0 | PSF-2.0 |
| winrt-runtime and the winrt-Windows.* packages | 4.1.0 / 10.0.28000.2957 | MIT |

No dependency in the project environment is under GPL (other than PyInstaller and its hooks, see
below), LGPL or AGPL. `certifi` (via the development HTTP client), `pathspec` (via Hatchling) and
`hypothesis` (tests) are MPL-2.0, a file-level license that allows commercial use when the files
are not modified. They are build or test tools and are not part of the installed programs.

## Build and installer tools

These produce the installers. Their code is bundled into the installed programs only where noted.

| Tool | Version | License | Notes |
|---|---|---|---|
| PyInstaller | 6.22.3 | GPL-2.0-or-later with a bootloader exception | Its bootloader is included in each installed program. The exception allows it to be used with software under any license. See <https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt>. |
| NSIS | 3.13 | zlib/libpng | Builds the setup programs. See <https://nsis.sourceforge.io/License>. |
| Hatchling | pinned in `uv.lock` | MIT | Builds the wheel. Not shipped. |
