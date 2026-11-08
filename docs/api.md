# API

`kodalo.api` is a FastAPI app over `kodalo.core`. Only the Kodalo window uses it: the routes are mounted inside the window (see [UI](ui.md)) and are not a public interface, so there is no server to start, no API key and no settings file. Routes only validate input, call the library and shape the response; logic stays in `kodalo.core`.

Cornea authenticates every request before it reaches a route (see [security](security.md)). The data folder is always the per-user default, `%LOCALAPPDATA%/Kodalo`; only the tests point it elsewhere.

All routes below are under `/api/v1` unless noted. In the tables, `{x}` is a path parameter, **Query** lists query-string parameters (`*` marks a required one) and **Body** names the request schema in [`openapi.json`](openapi.json).

- [Conventions](#conventions)
- [Probes and diagnostics](#probes-and-diagnostics)
- [Repositories](#repositories)
- [Studio](#studio)
- [Brands](#brands)
- [Palettes, layouts and canvases](#palettes-layouts-and-canvases)
- [Settings](#settings)
- [Cornea bridge](#cornea-bridge)
- [The contract](#the-contract)

## Conventions

- **Errors** use the problem-details format (`application/problem+json`). Common codes: `404` unknown item, `409` name already in use or item still referenced, `422` invalid data or a rejected file, `502` GitHub, Meta or an AI provider could not be reached or refused, `503` the local data cannot be opened (for example it was written by a newer version). Built-in palettes, layouts and canvases answer `403` when changed or deleted. A `500` never carries error details.
- **Creating** answers `201`; **deleting** answers `204`.
- **Plan** routes (`.../plan`) say what an AI request would send and estimate its tokens. They send nothing.
- Requests are limited to 1 MiB, except logo uploads (2 MB).

## Probes and diagnostics

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness probe (root, no authentication) |
| GET | `/ready` | Readiness probe (root, no authentication) |
| GET | `/doctor` | Diagnose the installation |

## Repositories

The Repositories page.

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| GET | `/repositories` | | List the added repositories |
| POST | `/repositories` | Body `RepoReadRequest` | Add a repository (same body and errors as `POST /studio/repositories`) |
| POST | `/repositories/check` | Body `StudioSourceRequest` | Check a folder or address against the saved GitHub mode without storing it. A folder returns values read from git to prefill a form, and `stored_id` when it was added before |
| GET | `/repositories/{repo_id}` | | Read one repository |
| DELETE | `/repositories/{repo_id}` | | Remove it with everything saved about it, images included |
| GET | `/repositories/{repo_id}/social-preview` | | The image the owner uploaded on GitHub (PNG or JPEG). `404` means none |
| GET | `/repositories/{repo_id}/icon` | | The repository's own icon (PNG, JPEG, WebP or SVG) found by the README analysis. `404` means none |

## Studio

Reading a repository and turning it into posts.

### Reading a repository

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| POST | `/studio/source` | Body `StudioSourceRequest` | Check a repository against the saved GitHub mode. Nothing is stored |
| GET | `/studio/repositories` | | List stored repositories |
| POST | `/studio/repositories` | Body `RepoReadRequest` (`refresh`, `details` for a local folder) | Read a repository (metadata, languages, structure, project files, monorepo flag, documentation found) and store it. A stored one is returned unless `refresh` is set. See [project files](repository-analysis.md#project-files) |
| GET | `/studio/repositories/{repo_id}` | | Read a stored repository |
| POST | `/studio/repositories/{repo_id}/analysis/plan` | | List what one AI request would send to find parser, framework and tooling configs |
| POST | `/studio/repositories/{repo_id}/analysis` | | Send that to the default AI model and save the valid configs. See [frameworks and tooling](repository-analysis.md#frameworks-and-tooling) |

### README analysis

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| GET | `/studio/repositories/{repo_id}/readme` | | The saved README analysis. `404` until it was read |
| POST | `/studio/repositories/{repo_id}/readme` | Body `ReadmeReadRequest` (`refresh`) | Read the README and the docs it links to (no AI). See [README analysis](repository-analysis.md#readme-analysis) |
| POST | `/studio/repositories/{repo_id}/readme/analysis/plan` | | List the documents one AI request would send |
| POST | `/studio/repositories/{repo_id}/readme/analysis` | | Send them to the default AI model and save purpose, installation methods, capabilities and use cases that have evidence |

### Ideas, copy and design

The post is identified by `brand_id`, `post_type`, `kind`, `name`, `idea_id` and `hook_id`.

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| GET | `/studio/repositories/{repo_id}/ideas` | Query `post_type*`, `kind`, `name` | The saved post ideas for a focus. `404` when none were made |
| POST | `/studio/repositories/{repo_id}/ideas/plan` | Body `IdeasRequest` | Plan the ideas request |
| POST | `/studio/repositories/{repo_id}/ideas` | Body `IdeasRequest` | Ask the AI for a strategy, angles with hooks, post ideas and claims to avoid. Replaces the ideas saved before |
| PUT | `/studio/repositories/{repo_id}/ideas/{idea_id}/posted` | Body `IdeaPostedUpdate` (`post_type`, `kind`, `name`, `posted`) | Flag an idea as posted, or clear the flag |
| GET | `/studio/repositories/{repo_id}/copy` | Query `brand_id*`, `post_type*`, `idea_id*`, `kind`, `name`, `hook_id` | The saved copy |
| POST | `/studio/repositories/{repo_id}/copy/plan` | Body `CopyRequest` | Plan the copy request |
| POST | `/studio/repositories/{repo_id}/copy` | Body `CopyRequest` | Ask the AI for slides, caption (with the repository URL), alternative opening, alt text and hashtags. Replaces the copy saved before; statements to avoid are listed in `warnings` |
| PUT | `/studio/repositories/{repo_id}/copy` | Body `CopyEdit` | Replace the saved copy with the user's edits |
| GET | `/studio/repositories/{repo_id}/design` | Same query as copy | The saved design: per slide template, alignment, picture, accent, icon, image source, plus `logo_box` and `warnings` |
| POST | `/studio/repositories/{repo_id}/design/plan` | Body `CopyRequest` | Plan the design request |
| POST | `/studio/repositories/{repo_id}/design` | Body `CopyRequest` | Ask the AI how to lay out each slide. Every choice is validated; anything else becomes the default with a warning |
| GET | `/studio/repositories/{repo_id}/design/slide` | Query as copy plus `slide*`, `mode` (`light` or `dark`) | The page of one slide, for a sandboxed frame |
| GET | `/studio/repositories/{repo_id}/design/svg` | Query as copy plus `slide*` | The cleaned drawing of one slide (`image/svg+xml`) |
| POST | `/studio/repositories/{repo_id}/design/export` | Body `ExportRequest` (`CopyRequest`, `mode`, `folder`) | Photograph each slide with Microsoft Edge into `slide-N.jpg` and write `caption.txt` into a new subfolder. Returns `folder`, `pictures`, `caption_file`. Errors include `503` when Edge is unavailable |
| POST | `/studio/repositories/{repo_id}/design/post` | Body `PostRequest` (`CopyRequest`, `mode`) | Post to Instagram (single image or carousel). Needs an Instagram canvas and cloudflared. Returns `media_id`, `permalink`. Can take a minute or two |

## Brands

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| GET | `/brands` | | List brand profiles |
| POST | `/brands` | Body `BrandCreate` | Create one from a palette (name or id) or from full data |
| POST | `/brands/import` | Query `name`; Body `BrandExport` | Add a profile from an exported file |
| POST | `/brands/contrast` | Body `ContrastRequest` | Check contrast of colors that may not be saved yet. Nothing is stored |
| GET | `/brands/fonts` | | The font catalogue: bundled fonts first, then installed fonts |
| GET | `/brands/{brand_id}` | | Read a profile |
| PATCH | `/brands/{brand_id}` | Body `BrandUpdate` | Rename or replace the data of a profile |
| DELETE | `/brands/{brand_id}` | | Delete a profile |
| POST | `/brands/{brand_id}/default` | | Make it the default |
| POST | `/brands/{brand_id}/duplicate` | Body `BrandDuplicate` | Copy a profile, logos included |
| GET | `/brands/{brand_id}/export` | | The profile and its logos as one file |
| PUT | `/brands/{brand_id}/logo` | Query `variant` (`light` or `dark`); Body the image file | Upload a logo (`image/png` or `image/svg+xml`, up to 2 MB). `413` above that, `415` for another type, `422` for an SVG with scripts, handlers, external links or entities |
| GET | `/brands/{brand_id}/logo` | Query `variant` | Show a logo, served with `nosniff` and a policy that allows no scripts or requests |
| DELETE | `/brands/{brand_id}/logo` | Query `variant` | Remove a logo |

A brand refers to a shared layout by `data.layout_id`, and a brand response also carries the resolved `layout` and its `canvas`. A brand export carries its layout and that layout's canvas by name and size; importing reuses a matching one or creates it.

## Palettes, layouts and canvases

All three sit under `/brands` and follow the same pattern. Built-in items come first in lists and answer `403` when changed or deleted; `duplicate` copies any item as one of your own.

| Resource | Base path | Body (create / update / duplicate / export) |
| --- | --- | --- |
| Palettes | `/brands/palettes` | `PaletteCreate` / `PaletteUpdate` / `PaletteDuplicate` / `PaletteExport` |
| Layouts | `/brands/layouts` | `LayoutCreate` / `LayoutUpdate` / `LayoutDuplicate` / `LayoutExport` |
| Canvases | `/brands/canvases` | `CanvasCreate` / `CanvasUpdate` / `CanvasDuplicate` / `CanvasExport` |

| Method | Path (relative to the base path) | Query | Purpose |
| --- | --- | --- | --- |
| GET | `` | | List (each with its complete data; layouts show which brands use them, canvases their platform and a size concern) |
| POST | `` | | Create |
| POST | `/import` | `name` | Add one from an exported file |
| GET | `/{id}` | | Read |
| PATCH | `/{id}` | | Change |
| DELETE | `/{id}` | | Delete. A layout used by brands, or a canvas used by layouts, answers `409` |
| POST | `/{id}/duplicate` | | Copy |
| GET | `/{id}/export` | | Export as a file (a layout includes its canvas) |

Palette-only routes:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/brands/palettes/suggest/plan` | Estimate what the AI palette suggestion would send and cost (provider, model, tokens) |
| POST | `/brands/palettes/suggest` | Ask the default AI model for a new palette that differs from the existing ones. Nothing is saved |

A layout refers to a canvas by `canvas_id` and holds the margins, corner radius, text settings and the number of slides (6 by default). Changing a canvas or a layout changes everything that uses it.

Related: `GET /social-platforms` lists the social platforms (Instagram, Custom) with the sizes each recommends.

## Settings

### GitHub, logs and theme

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| GET, PUT | `/settings/github` | `GitHubSettingsUpdate` | How Kodalo reaches GitHub: `mode` (`gh_cli` by default, `local_folder`, `web_fetch`) and `manifest_limit` (1 to 100, default 10) |
| POST | `/settings/github/check` | | Try the saved way once. A failure is reported in the body |
| GET, PUT | `/settings/logs` | `LogsUpdate` | Log level (`INFO` by default) and retention in days (90 by default). Applies at once; the response names the log folder |
| GET, PUT | `/settings/theme` | `ThemeUpdate` | Window theme: `system` (default), `light`, `dark` |

### AI connections and models

`{provider}` is `claude_api`, `claude_code`, `chatgpt_api` or `gemini_api`. API keys go to the system keychain and are never returned, only their last characters (`key_hint`).

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| GET | `/settings/ai/connections` | | Every provider with its connection and models, saved or not |
| PUT | `/settings/ai/connections/default` | `AiDefaultConnection` | Make a saved, enabled connection the default |
| PUT | `/settings/ai/connections/{provider}` | `AiConnectionUpdate` (`enabled`, `api_key`, `base_url`) | Save a connection. Anything left out is kept |
| DELETE | `/settings/ai/connections/{provider}` | | Forget it with its models and key |
| POST | `/settings/ai/connections/{provider}/test` | | Try the connection. A failure is reported in the body |
| GET | `/settings/ai/connections/{provider}/models` | | The saved models |
| POST | `/settings/ai/connections/{provider}/models/refresh` | | Ask the provider for its models and save them. Models added by hand are kept. `502` when unreachable |
| GET | `/settings/ai/connections/{provider}/model-defaults` | Query `name*` | The `max_tokens`, `temperature` and `timeout_s` a model starts with |
| PUT | `/settings/ai/connections/{provider}/models/{name}` | `AiModelUpdate` | Add a model or change its settings. A new model gets standard values for any left out; for a saved model they replace the saved ones |
| DELETE | `/settings/ai/connections/{provider}/models/{name}` | | Forget a model |
| PUT | `/settings/ai/connections/{provider}/default-model` | `AiDefaultModel` | Choose the connection's default model |
| GET | `/settings/ai/task-models` | | The six AI jobs (`palette`, `repo_metadata`, `repo_features`, `studio_ideas`, `studio_copy`, `studio_design`) with the chosen `model`, or `null` for the default |
| PUT | `/settings/ai/task-models/{task}` | `AiTaskModelUpdate` | Choose a model for one job, or `null` for the default. `404` for a model the connection lacks |
| GET, PUT | `/settings/ai/studio-ideas` | `AiIdeaCount` | How many post ideas Studio asks for (`idea_count`, 1 to 20, 5 by default) |

### AI history and usage

| Method | Path | Query / Body | Purpose |
| --- | --- | --- | --- |
| GET | `/settings/ai/history` | Query `period` (`day`, `week`, `month`, `year`, `all`, `custom`), `start`, `end` (`2026-11-01`), `limit` (1 to 200), `offset` | The calls made to AI providers, newest first, without their text |
| GET | `/settings/ai/history/{call_id}` | | One call with `prompt_text` and `reply_text` (`null` when not kept) |
| DELETE | `/settings/ai/history` | | Remove every entry and return how many (`deleted`) |
| GET, PUT | `/settings/ai/history/settings` | `AiHistorySettingsUpdate` | `store_text` (off by default) and `retention_days` (90 by default, 0 keeps all) |
| GET | `/settings/ai/usage` | Query `period`, `start`, `end` | Calls and tokens per connection and model, and per UTC day. Failed calls count 0 tokens |

### Platforms

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| GET, PUT | `/settings/platforms/{platform}` | `PlatformSettingsUpdate` | Hashtag count (`hashtag_count`, 0 to 30, 5 by default), `default_hashtags`, and the visuals the designer may use (`use_social_preview`, `use_repo_icon`, `use_icons`, `build_custom_images`, `use_ai_templates`). `platform` is `instagram`. `422` when there are more default hashtags than `hashtag_count` |
| GET | `/settings/platforms/instagram/connection` | | The Instagram connection: `username`, `account_id`, `account_type`, `connected_at`, `token_hint` |
| PUT | `/settings/platforms/instagram/connection` | `InstagramConnectRequest` (`access_token`, `account_id`) | Check the token with Meta and keep it in the keychain. `422` malformed, `502` Meta refused it |
| DELETE | `/settings/platforms/instagram/connection` | | Disconnect |
| POST | `/settings/platforms/instagram/connection/check` | | Re-check. `404` when not connected |
| GET | `/settings/platforms/instagram/tunnel` | | Whether cloudflared, which posting needs, is installed (`installed`). Installs nothing |
| POST | `/settings/platforms/instagram/tunnel` | | Install it when missing (winget, else a checked download into the data folder). Can take a minute |

## Cornea bridge

Besides the routes above, the window talks to Cornea Shell's bridge at `POST /api/bridge/<action>`. These are native actions (system dialogs, notifications, files) and exist only inside the window. The frontend calls them from `src/libs/api.js`. The body is JSON and every call is authenticated by Cornea's session like the routes above.

Each answer is `{"available": true, "result": ...}`, or `{"available": false, "reason": "..."}` when the action cannot run, for example in a page opened in a browser. The frontend then falls back or tells the user.

| Action | Body | Result | Purpose |
| --- | --- | --- | --- |
| `show_notification` | `title` (up to 64 characters), `message` (up to 256) | none | Windows notification when a task finishes. Cornea built-in; the app enables it with `Bridge(notifications=True)` and never fails if it is off |
| `save_file` | `filename`, `file_types` | the chosen path, or empty when cancelled | System save dialog. Cornea built-in |
| `choose_folder` | none | the chosen folder, or empty when cancelled | System folder dialog. Cornea built-in |
| `open_external` | `url` | none | Open a web address in the system browser. Cornea built-in; outside the window the page opens it in a new tab |
| `app_info` | none | `{"name", "version"}` | The app name and version. Registered by Kodalo |
| `write_json_file` | `path`, `text` | none | Save an export to the file chosen with `save_file`. Registered by Kodalo. Only a `.json` file in an existing local folder is accepted (no network paths), and `text` is limited in size |

The window mounts the routes above under Cornea's `/api` prefix, so they appear as `/api/v1/...`. Cornea serves the built frontend and the API from one address.

## The contract

`docs/openapi.json` is generated by `uv run python scripts/export_openapi.py`. CI fails when it is out of date, `api-compat.yml` warns about breaking changes on pull requests, and a Schemathesis test (`tests/api/integration/`) fuzzes the app in-process for server errors. The app serves no interactive docs. Put breaking changes in a new `/api/v2` router.
