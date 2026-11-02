# Kodalo

[![CI](https://github.com/coldsofttech/Kodalo/actions/workflows/ci.yml/badge.svg)](https://github.com/coldsofttech/Kodalo/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/Kodalo)](https://pypi.org/project/Kodalo/)
[![Python versions](https://img.shields.io/pypi/pyversions/Kodalo)](https://pypi.org/project/Kodalo/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/github/license/coldsofttech/Kodalo)](LICENSE)
[![Built with Cornea Shell](https://img.shields.io/badge/built%20with-Cornea%20Shell-blue)](https://github.com/coldsofttech/CorneaShell)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Typer](https://img.shields.io/badge/Typer-CLI-black)](https://typer.tiangolo.com/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-installers-blue)](https://pyinstaller.org/)
[![NSIS](https://img.shields.io/badge/NSIS-Windows%20setup-blue)](https://nsis.sourceforge.io/)
[![nfpm](https://img.shields.io/badge/nfpm-deb%20%26%20rpm-blue)](https://nfpm.goreleaser.com/)

Kodalo turns your GitHub repositories into accurate, on-brand Instagram posts. It runs on your Windows desktop, keeps your products and content history on your own computer, and lets you choose your own AI provider. Nothing is posted without your approval.

> Kodalo is under development and not released yet.

## What it will do

- Read a GitHub repository, or a product you describe yourself, and list its features for you to review
- Write single-image posts and carousels, with every claim traced back to the repository
- Keep your brand colors, fonts and logo consistent across posts
- Warn you before you repeat a feature or angle you have already promoted
- Export finished images and captions for you to post
- Work with Gemini, Claude Code or any OpenAI-compatible provider, using your own credentials

## Installation

The Python package gives you the command line (`kodalo`). Requires Python 3.11 or newer. The recommended way to install a tool is in its own isolated environment:

```bash
uv tool install Kodalo
```

Or with pipx:

```bash
pipx install Kodalo
```

For the desktop window, use the Windows installer. The API and the window are not part of the Python package. Or use a ready-made installer from the [releases page](https://github.com/coldsofttech/Kodalo/releases), where each file has a checksum in `SHA256SUMS.txt`:

- **Windows:** the setup program installs for you or for everyone, and can add the command to your PATH. winget and Scoop are available once the maintainer enables them.
- **Linux:** a `.deb` (Debian, Ubuntu) or `.rpm` (Fedora) package.
- **macOS:** Homebrew, once the maintainer enables it.

See the [releasing guide](docs/releasing.md) for the install commands of each.

The window needs Windows 10 or 11 with the Microsoft Edge WebView2 runtime, which is already installed on current versions. You do not need Node to use the installed tool.

## Usage

`kodalo-ui` opens the app window, where you set up your brand: colors for light and dark posts, fonts, a logo and the layout, with a live preview of sample slides. `kodalo-ui --no-window` prints an address you can open in a browser instead. On other systems it explains that the window needs Windows; the command line and the API work everywhere. Under Settings you choose how Kodalo reaches GitHub: the GitHub CLI (the default), a folder of repositories on your computer, or the web for public repositories. `kodalo --help` lists the commands.

The repository, catalog and post workflow is still being built, so the available commands are limited for now.

See the [CLI reference](docs/cli.md) for every command, option and exit code, and the [API guide](docs/api.md) to run the API on its own.

## Development

```bash
git clone https://github.com/coldsofttech/Kodalo.git
cd Kodalo
uv sync
npm ci --prefix src/kodalo_ui/ui
npm run build --prefix src/kodalo_ui/ui
uv run python -m kodalo_ui
```

See the [development guide](docs/development.md) for testing, hot reload, linting and releasing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please report security issues privately as described in [SECURITY.md](SECURITY.md).

## License

Released under the [MIT License](LICENSE).
