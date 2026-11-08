# Kodalo

[![CI](https://github.com/coldsofttech/Kodalo/actions/workflows/ci.yml/badge.svg)](https://github.com/coldsofttech/Kodalo/actions/workflows/ci.yml)
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

Kodalo is an AI-powered social media content studio for your GitHub projects. It reads your repositories and turns them into accurate, on-brand posts, starting with Instagram. It runs on your Windows desktop, keeps your repositories, brands and content history on your own computer, and lets you choose your own AI provider. Nothing is posted without your approval.

## What it does

- Reads a GitHub repository (through the GitHub CLI, a folder on your computer, or the web) and works out what the product is: languages, frameworks, tooling, purpose, how to install it and what it can do
- Suggests post ideas, writes the copy and designs single-image posts and carousels, with every claim traced back to the repository
- Keeps your brand colors, fonts, logo and layout consistent across posts, with a live preview
- Exports finished pictures and captions for you to post, or posts to Instagram when you choose to
- Works with Claude (API or Claude Code), ChatGPT or Gemini, using your own credentials; every AI request shows what it will send and what it will cost, and asks first

## Installation

Kodalo is installed with a Windows setup program from the [releases page](https://github.com/coldsofttech/Kodalo/releases). Each release has two setups and a `SHA256SUMS.txt` to check your download:

| File | What it installs |
| --- | --- |
| `kodalo-<version>.setup.exe` | The desktop window |
| `kodalo-cli-<version>.setup.exe` | The `kodalo` command line, and can add it to your PATH |

Both can install for just you or for everyone, and remove cleanly from Settings > Apps. You do not need Python or Node. The window needs Windows 10 or 11 with the Microsoft Edge WebView2 runtime, which current versions already have. Windows may warn about the setup because it is not code-signed. See [packaging](docs/packaging.md) for silent installs and how releases are built.

## Getting started

1. Open **Kodalo** and, under **Settings**, choose how Kodalo reaches GitHub and connect an AI provider with your own key.
2. Under **Brands**, create a brand from a starter palette: colors for light and dark posts, fonts, a logo and a layout. You can keep your own palettes, layouts and canvases and reuse them.
3. Under **Repositories**, add a repository by folder or GitHub address. Kodalo reads it and remembers it.
4. In **Studio**, pick the repository and what to post about. Kodalo suggests ideas, writes the copy and designs the slides, asking before every AI request.
5. Export the pictures and caption, or post to Instagram once you have connected your account in Settings.

Everything in the window is also available from the command line:

```console
kodalo repositories add https://github.com/owner/name
kodalo studio ideas make <repository-id>
kodalo brand create Main --palette paper
```

Run `kodalo --help` for the list. See the [CLI reference](docs/cli.md) for every command and option.

## Your data

Kodalo stores everything in `%LOCALAPPDATA%\Kodalo`. API keys and the Instagram token go to the Windows Credential Manager, never to a file. Nothing leaves your computer except the requests you approve to your AI provider, GitHub, and Instagram when you post. See [security](docs/security.md).

## Documentation

| Guide | What is in it |
| --- | --- |
| [CLI](docs/cli.md) | Every command, argument, option and exit code |
| [User guide](docs/ui-user-guide.md) | A screen-by-screen tour of the window, with screenshots |
| [UI](docs/ui.md) | The window, its screens and design decisions |
| [API](docs/api.md) | The routes the window uses and the Cornea bridge |
| [Repository analysis](docs/repository-analysis.md) | How project files, frameworks and the README are read |
| [Architecture](docs/architecture.md) | How the pieces fit together |
| [Security](docs/security.md) | Secrets, AI requests and posting |
| [Packaging](docs/packaging.md) | Building the installers and making a release |
| [Third-party notices](docs/third-party-notices.md) | Open source components Kodalo uses |
| [Development](docs/development.md) | Setting up, testing and CI |

## Development

```bash
git clone https://github.com/coldsofttech/Kodalo.git
cd Kodalo
uv sync
npm ci --prefix src/kodalo/ui/ui
npm run build --prefix src/kodalo/ui/ui
uv run python -m kodalo.ui
```

See the [development guide](docs/development.md) for testing, hot reload and linting.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please report security issues privately as described in [SECURITY.md](SECURITY.md).

## License

Released under the [MIT License](LICENSE). Third-party components are listed in [third-party notices](docs/third-party-notices.md).
