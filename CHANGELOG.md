# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Canvases, palettes and layouts (with a number of slides, 6 by default) you can create, export, import and reuse across brands, from `kodalo brand` and the Brands screen.
- `kodalo brand show` is grouped and shows color swatches; `brand settings list` and `brand settings set` replace `brand set`.
- Studio screen and `kodalo studio` commands read a repository's details, languages and top-level files (from the GitHub CLI, the web or a local folder) and remember them; manifests, frameworks and tooling come next.
- GitHub connectivity setting: choose the GitHub CLI (default), a local folder or web fetch, with `kodalo settings github` or in the new Settings screen.
- Brand profiles (colors, fonts, logo and layout) can be created and managed with `kodalo brand`.
- The Kodalo window lets you create and edit brands (colors, fonts, logo, layout) with a live preview, and has an About page that checks your installation.
- Local database that stores your products and settings on your computer and updates itself safely when Kodalo is upgraded.
