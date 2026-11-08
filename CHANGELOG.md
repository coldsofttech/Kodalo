# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-08

### Added

- Kodalo for Windows, as a window and a command line (`kodalo`). Each has its own setup, with the Kodalo icon, license page and ColdSoft Technologies as publisher, and the command line also comes as a portable zip.
- The window opens straight away on a branded loading screen, starts on a Home page with shortcuts, and has an About page that checks your installation.
- Settings > Appearance: choose a light or dark theme, or follow the system (the default).
- Windows notifications when a task finishes or fails, such as analyzing a repository, generating Studio posts or checking a connection.
- A local database on your computer holds your repositories, brands and settings, and updates itself safely when Kodalo is upgraded.
- Daily log files in the data folder's `logs` folder. Settings > Logs (or `kodalo settings logs`) sets the level and how many days they are kept (90 by default).
- Opening a page always shows current data, and asks before discarding unsaved changes.
- Brands (`kodalo brand`): profiles with colors, fonts, logo and layout, created and edited with a live preview, and shown full screen with arrow keys to step through slides.
- Reusable palettes, canvases and layouts that you can create, export, import and share across brands. Canvases have a social platform (Instagram or Custom) and warn about sizes it does not recommend; the logo can be hidden on any slide.
- Suggest with AI on Palettes proposes a name and colors that differ from your existing ones, after showing where the request goes and the tokens it uses.
- Repositories (`kodalo repositories`): add, list, show and remove repositories, read from the GitHub CLI, the web or a local folder. Shows the social preview image and the repository's own icon.
- Reading a repository finds its languages, README, changelog, license and docs, notable folders, monorepo layout, project files (npm, Python, Rust, Go, Java, .NET and more) with their packages and dependencies, and what was left unread. Your own JSON files can teach Kodalo new project files, frameworks and tooling.
- Reading also detects frameworks and tooling (React, FastAPI, Vite, Ruff, GitHub Actions, Docker, uv and about 120 more) and shows what revealed each.
- Settings > GitHub: choose the GitHub CLI (default), a local folder or web fetch, and how many project files, documents and how much of each (up to 2000 KB) to read.
- Settings > AI: connect Claude API, Claude Code, ChatGPT API or Gemini API, with keys in the system keychain, a default model and a connection test. Only one connection is active at a time, and Claude Code calls stay small.
- Settings > AI > Models per job: choose which model suggests palettes, reads repositories and writes and designs Studio posts. Models start with sensible limits for their kind, and you choose how many post ideas Studio asks for (1 to 20, 5 by default).
- Refresh with AI (and `--refresh-with-ai`) makes one request to your AI model to learn unknown project files and list the product's capabilities, use cases and features, with their importance, maturity and claims to repeat with care. It shows the tokens it expects and asks first, with a see-through progress screen while it works.
- AI history lists every call with date, purpose, connection, model and tokens, with token tables and charts, filters, optional prompt and answer storage, CSV or JSON export and a Purge button (`kodalo settings ai history`). Entries older than 90 days are removed automatically.
- Studio (`kodalo studio`) walks from a repository to a finished Instagram post. Repository and Analyze steps read the README and linked docs, with or without AI, and show what the product is for, how to install it and what it can do.
- Studio's Focus step picks a Tool / Utility post or a Feature post, and Next with AI plans it: a strategy, three angles and post ideas as cards you can choose, copy and fold open. Ideas are kept, refreshed by adding new ones to the saved ones, and marked Posted once published.
- Studio writes the slides, caption, alt text and hashtags of the chosen idea with the AI, which you can edit and save.
- Studio designs the post: each slide gets a template, picture and icon, shown full screen with the caption and hashtags. With AI-powered templates on, the AI writes one shared style and a layout per slide, while Kodalo places your text, brand logo or repository name, footer and progress marks.
- Posts can be written and designed for Instagram and custom canvases. Settings > Platforms sets the number of hashtags, default hashtags, visuals the designer may use and, for Instagram, the access token and account ID (checked with Instagram and kept in the system keychain). Captions include the repository URL between the call to action and the hashtags.
- Post publishes a post to Instagram, installing the third-party tool Cloudflared if needed. Export saves the slides as pictures and the caption as a text file, or as HTML or SVG from the command line, to post by hand.
