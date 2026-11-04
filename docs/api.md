# API

`kodalo.api` is a FastAPI app over `kodalo.core`. Only the Kodalo window uses it: the routes are mounted inside the window (see [UI](ui.md)) and are not a public interface, so there is no server to start, no API key and no settings file. Routes only validate input, call the library and shape the response; logic stays in `kodalo.core`.

Cornea authenticates every request before it reaches a route (see [security](security.md)). The data folder is always the per-user default, `%LOCALAPPDATA%/Kodalo`; only the tests point it elsewhere.

## Endpoints

| Method and path | Purpose |
| --- | --- |
| `GET /health`, `GET /ready` | Liveness and readiness probes, no authentication |
| `GET`, `PUT /api/v1/settings/github` | Read or choose how Kodalo reaches GitHub (`gh_cli` by default, `local_folder`, `web_fetch`) and `manifest_limit`, how many project files to read from GitHub (1 to 100, default 10) |
| `GET /api/v1/settings/ai/connections` | Every AI provider (`claude_api`, `claude_code`, `chatgpt_api`, `gemini_api`) with its connection and models, saved or not. The API key is never returned, only its last characters (`key_hint`) |
| `PUT`, `DELETE /api/v1/settings/ai/connections/{provider}` | Save a connection (`enabled`, `api_key`, `base_url`; anything left out is kept) or forget it with its models and key. The key goes to the system keychain |
| `PUT /api/v1/settings/ai/connections/default` | Make a saved, enabled connection the default |
| `POST /api/v1/settings/ai/connections/{provider}/test` | Try the connection; a failure is reported in the body, not as an error |
| `GET /api/v1/settings/ai/connections/{provider}/models` | The saved models |
| `POST /api/v1/settings/ai/connections/{provider}/models/refresh` | Ask the provider for its models and save them (502 when it cannot be reached); models added by hand are kept |
| `PUT`, `DELETE /api/v1/settings/ai/connections/{provider}/models/{name}` | Add a model or change its `max_tokens`, `temperature` and `timeout_s`, or forget it. A new model gets Kodalo's standard settings (see `core/ai/defaults.py`) for any left out; for a saved model they replace the saved ones, so a missing one is cleared |
| `PUT /api/v1/settings/ai/connections/{provider}/default-model` | Choose the model the connection uses by default |
| `GET`, `PUT /api/v1/settings/theme` | Read or choose the window theme (`system` by default, `light`, `dark`); only the window uses it |
| `POST /api/v1/settings/github/check` | Try the saved way once; a failure is reported in the body, not as an error |
| `POST /api/v1/studio/source` | Check a repository against the saved GitHub mode (a folder, or a GitHub address); nothing is stored. For a folder it returns values read from git to prefill a form, and `stored_id` when it was read before |
| `POST /api/v1/studio/repositories` | Read a repository (metadata, languages, top-level structure, notable folders, project files with their package name, version and dependencies, and a monorepo flag with its reasons; see [manifest-parsers.md](manifest-parsers.md)) and store it; a stored one is returned unless `refresh` is set. A local folder needs `details` the first time. Errors: `404` no such repository, `422` invalid source or missing details, `502` GitHub or `gh` unreachable |
| `POST /api/v1/studio/repositories/{id}/parsers/plan` | List the top-level project files no parser config covers and estimate the tokens asking the default AI would use. Nothing is sent. Errors: `404`, `422` (no default connection or model), `502` |
| `POST /api/v1/studio/repositories/{id}/parsers` | Send the start of those files to the default AI model (secret-looking lines removed, at most 5 files), and save each valid parser config to the `parsers` folder. Read the repository again to use them. Errors as above |
| `GET /api/v1/studio/repositories`, `GET /api/v1/studio/repositories/{id}` | List stored repositories, read one |
| `GET`, `POST /api/v1/palettes` | List palettes (built-in first, each with complete brand data to begin from), create one |
| `GET`, `PATCH`, `DELETE /api/v1/palettes/{id}` | Read, rename or recolor, delete a palette. Built-in palettes answer `403` |
| `POST /api/v1/palettes/{id}/duplicate` | Copy any palette as a palette of your own |
| `POST /api/v1/palettes/suggest` | Ask the default AI model for a new palette (name and colors) that differs from the existing ones; nothing is saved |
| `GET /api/v1/palettes/{id}/export`, `POST /api/v1/palettes/import` | Export a palette as a file; add one from a file (`?name=` sets its name) |
| `GET`, `POST /api/v1/layouts` | List layouts (built-in first, each with the layouts that use it), create one |
| `GET`, `PATCH`, `DELETE /api/v1/layouts/{id}` | Read, change, delete a layout. Built-in layouts answer `403`; deleting one that brands use answers `409` |
| `POST /api/v1/layouts/{id}/duplicate` | Copy any layout as a layout of your own |
| `GET /api/v1/layouts/{id}/export`, `POST /api/v1/layouts/import` | Export a layout (with its canvas) as a file; add one from a file |
| `GET /api/v1/brands/fonts` | The font catalogue: bundled fonts first, then fonts installed on this computer |
| `GET`, `POST /api/v1/canvases` | List canvases (built-in first, each with the brands that use it), create one |
| `GET`, `PATCH`, `DELETE /api/v1/canvases/{id}` | Read, rename or resize, delete a canvas. Built-in canvases answer `403`; deleting one that layouts use answers `409` |
| `POST /api/v1/canvases/{id}/duplicate` | Copy any canvas as a canvas of your own |
| `GET /api/v1/canvases/{id}/export`, `POST /api/v1/canvases/import` | Export a canvas as a file; add one from a file |
| `POST /api/v1/brands/contrast` | Check colors that may not be saved yet; nothing is stored |
| `GET`, `POST /api/v1/brands` | List brand profiles, create one from a palette or from full data |
| `POST /api/v1/brands/import` | Add a profile from an exported file (`?name=` sets its name) |
| `GET`, `PATCH`, `DELETE /api/v1/brands/{id}` | Read, rename or replace the data of, delete a profile |
| `POST /api/v1/brands/{id}/default` | Make a profile the default |
| `POST /api/v1/brands/{id}/duplicate` | Copy a profile, including its logo files |
| `GET /api/v1/brands/{id}/export` | The profile and its logos as one file |
| `PUT`, `GET`, `DELETE /api/v1/brands/{id}/logo?variant=light\|dark` | Upload, show, remove a logo |

A brand refers to a shared layout by `data.layout_id`, and a brand response also carries the resolved `layout` and its `canvas`. A layout refers to a canvas by `canvas_id` and holds the margins, corner radius, text settings and the number of slides (6 by default). Changing a canvas or a layout changes everything that uses it. A brand export carries its layout and that layout's canvas by name and size; importing reuses a matching layout or canvas, or creates one. `palette` on brand creation is the name or id of a palette.

Errors use the problem-details format (`application/problem+json`): `404` for an unknown profile, `409` for a name already in use, `422` for invalid data or a rejected file, `503` if the local data cannot be opened (for example it was written by a newer version).

### Logos

`PUT /brands/{id}/logo` takes the file itself as the request body, with `Content-Type: image/png` or `image/svg+xml`, up to 2 MB (`413` above that, `415` for another type). SVG files that contain scripts, event handlers, external links or entities are refused with `422`. `GET` returns the file with `X-Content-Type-Options: nosniff` and a content security policy that allows no scripts or requests, so it can be shown in an image tag but never run. Other requests are limited to 1 MiB; logo uploads have their own 2 MB limit.

## The contract

`docs/openapi.json` is generated by `uv run python scripts/export_openapi.py`. CI fails when it is out of date, `api-compat.yml` warns about breaking changes on pull requests, and a Schemathesis test (`tests/api/integration/`) fuzzes the app in-process for server errors. The app serves no interactive docs. Put breaking changes in a new `/api/v2` router.
