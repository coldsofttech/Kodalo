# Development

How to work on Kodalo locally. For how the pieces fit together, see [architecture](architecture.md).

## Setup

You need [uv](https://docs.astral.sh/uv/) (Python 3.11 or newer) and, for the window's frontend, Node (version in `src/kodalo/ui/ui/.nvmrc`). The window itself runs on Windows only; everything else works on any system.

```bash
uv sync                          # create .venv and install the dev dependencies
npm ci --prefix src/kodalo/ui/ui # install the frontend exactly as package-lock.json says
uv run pre-commit install --hook-type pre-commit --hook-type post-commit   # optional: checks on every commit (post-commit is for the Sweepito cleanup)
```

## Layout

```text
src/kodalo/core/     library: all the logic, never prints or exits
src/kodalo/cli/      Typer + Rich command line (see cli.md)
src/kodalo/api/      FastAPI routes the window calls (see api.md)
src/kodalo/ui/       Cornea Shell wiring and the `kodalo-ui` command (see ui.md)
src/kodalo/ui/ui/    React + Vite frontend (JavaScript)
tests/               pytest tests: core/, cli/, api/, ui/, each with an integration/ folder
installer/           PyInstaller specs and NSIS scripts (see packaging.md)
scripts/             OpenAPI export, installer build, release notes
docs/                documentation, including the generated openapi.json
```

## Everyday commands

```bash
uv run kodalo --help                # the command line
uv run python -m kodalo.ui          # the window (Windows)
uv run python -m kodalo.ui --dev    # the window on the Vite dev server, with hot reload
uv run python -m kodalo.ui --no-window   # serve the UI for a browser instead
```

| Task | Command |
| --- | --- |
| Unit tests with coverage (80% minimum, skips integration) | `uv run pytest` |
| One component | `uv run pytest tests/api --no-cov` |
| Integration tests only | `uv run pytest -m integration --no-cov` |
| Lint and format | `uv run ruff check .` and `uv run ruff format .` |
| Type check (strict) | `uv run mypy` |
| Regenerate the OpenAPI document | `uv run python scripts/export_openapi.py` |
| Frontend lint, tests, build | `npm run lint`, `npm test`, `npm run build` in `src/kodalo/ui/ui` |

Tests in any `integration/` folder are marked `integration` by `tests/conftest.py`. They are skipped by default and in pre-commit, and run as their own CI job. They include a Schemathesis contract test and, on Windows with a built frontend, a real Cornea server without a window.

Change a route or schema, and `docs/openapi.json` must be regenerated (CI fails when it is out of date). Change a command or option, and update [cli](cli.md) by hand.

## Continuous integration

The `ci` workflow runs `lint` (pre-commit and the OpenAPI check), `ui` (frontend lint, tests and build), `test` (Python 3.11 to 3.15 on Windows), `integration` and `ui-windows` (the real Cornea test against the built frontend). A final `ci` job gates on all of them and is a required check. The other workflows are listed in [architecture](architecture.md#workflows).

## Repository settings

Repository settings are not stored in the repo, so they are applied by hand (Settings on GitHub):

| Setting | Value |
| --- | --- |
| Dependency graph, Dependabot alerts and security updates | On |
| Secret protection | On, with push protection |
| CodeQL | Default setup (it needs a supported language in the repo) |
| Malware alerts, Private vulnerability reporting | On (Settings > Advanced Security) |
| Copilot Autofix | Off |

The `main` ruleset is in `.github/rulesets/main.json`; import it under Settings > Rules. It blocks deletion and force pushes, and requires a pull request (code owner review, resolved conversations, squash merge only), the `ci` and `dependency-review` checks with the branch up to date, and CodeQL results. Enable "Require code quality results" in the ruleset UI by hand, as the JSON does not include it. Repository admins can bypass the ruleset through a pull request, so a solo maintainer can merge despite the code owner rule (authors cannot approve their own pull requests); remove the bypass actor if there are more maintainers.

Some scripts look optional but workflows run them, so do not delete them: `scripts/export_openapi.py` (`ci.yml` checks `docs/openapi.json`), `scripts/build_installer.py` and `installer/` (`build.yml`, `release.yml`), `scripts/update_manifests.py` (release notes) and `installer/projectinfo.py` (project names for every workflow).

## Releasing

Publishing a GitHub release runs `release.yml`, which builds the Windows installers and attaches them. See [packaging](packaging.md#releasing).
