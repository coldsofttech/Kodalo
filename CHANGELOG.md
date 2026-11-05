# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Reading a repository now also shows its README, changelog, contributing and license files and docs folder, the line that shows each project file's package, and which files were left unread (secret-looking, over 200 KB or unreadable).
- Settings has a new AI History tab: every AI call with its date, purpose, connection, model and tokens, a token table and chart per connection and model, filters (last day, week, month, year, custom), the full prompt and answer if you choose to keep them, and a Purge button. `kodalo settings ai history`, `usage`, `history-settings` and `purge-history` do the same. Entries older than 90 days (changeable) are removed automatically.
- Reading a repository now also lists its tooling (build, test, lint and format, CI, containers and package tools such as Make, Ruff, GitHub Actions, Docker or uv); `Refresh with AI` learns more, and your own JSON files can add more.
- Reading a repository now lists the frameworks and tools it uses (React, FastAPI, Vite and about 120 more) with what showed them; `Refresh with AI` also asks your default AI model about packages Kodalo does not know, and your own JSON files can add more.
- New palettes: `Suggest with AI` fills in a name and colors that differ from your existing palettes, for you to review before creating.
- Studio can ask your default AI model to teach Kodalo project files it does not know yet (`Refresh with AI` in the window, `--refresh-with-ai` on the command line). It shows the tokens it expects to use and asks before sending anything.
- `Refresh with AI` now makes one request to your AI model instead of two, so it asks once and uses fewer tokens.
- AI models start with sensible max tokens, temperature and timeout for their kind (Opus, Sonnet, Haiku, Gemini, GPT).
- AI Connections setting: connect Claude API, Claude Code, ChatGPT API or Gemini API, with API keys kept in the system keychain, a default model per connection, and tests that check each connection works, in `kodalo settings ai` and the Settings screen.
- Reading a repository also reports its notable folders, whether it is a monorepo, and the package name, version and dependencies of its project files (npm, Python, Rust, Go, Java, .NET and more); rescan stored repositories to fill them in.
- New GitHub setting for how many project files to read (10 by default), and your own JSON files can teach Kodalo new kinds of project files.
- Settings has an Appearance tab to choose a light or dark theme, or follow the system (the default).
- The window opens on a new Home page and loads each screen only when you first open it.
- Canvases, palettes and layouts (with a number of slides, 6 by default) you can create, export, import and reuse across brands, from `kodalo brand` and the Brands screen.
- `kodalo brand show` is grouped and shows color swatches; `brand settings list` and `brand settings set` replace `brand set`.
- Studio screen and `kodalo studio` commands read a repository's details, languages and top-level files (from the GitHub CLI, the web or a local folder) and remember them; manifests, frameworks and tooling come next.
- GitHub connectivity setting: choose the GitHub CLI (default), a local folder or web fetch, with `kodalo settings github` or in the new Settings screen.
- Brand profiles (colors, fonts, logo and layout) can be created and managed with `kodalo brand`.
- The Kodalo window lets you create and edit brands (colors, fonts, logo, layout) with a live preview, and has an About page that checks your installation.
- Local database that stores your products and settings on your computer and updates itself safely when Kodalo is upgraded.

### Changed

- Using Claude Code as the AI connection now sends only Kodalo's own question, so a call uses about 1,700 tokens instead of about 37,000.
- Kodalo starts a little faster.
