# UI

The desktop window is hosted by [Cornea Shell](https://github.com/coldsofttech/CorneaShell) (`cornea-shell`). It runs on Windows only; the library and command line work everywhere. The window is a React single-page app that talks to Python while it runs.

## How it works

Cornea serves the built files (`src/kodalo/ui/ui/dist`) and the API from one address, behind a start-up token that becomes a session cookie (see [security](security.md)). The page reaches Python in two ways, both only through `src/libs/api.js`:

- **Data:** `fetch('/api/v1/...')` calls the `kodalo.api` routes ([API](api.md)).
- **Native actions:** `POST /api/bridge/<action>` for file and folder dialogs, notifications, opening links and `app_info` ([Cornea bridge](api.md#cornea-bridge)). Outside the window there is no bridge, so the page falls back or tells the user.

```text
src/kodalo/ui/__main__.py   the `kodalo-ui` command: options, output, exit code
src/kodalo/ui/app.py        builds the Cornea shell: serves dist, mounts the API, registers actions
src/kodalo/ui/ui/           React + Vite (JavaScript): src/, index.html, package.json, tests
src/kodalo/ui/ui/dist/      build output, not committed; frozen into the Windows build
```

`app.py` only wires things together and holds no business logic. `kodalo.api` and `kodalo.core` never import `kodalo.ui`.

```bash
npm ci --prefix src/kodalo/ui/ui && npm run build --prefix src/kodalo/ui/ui
uv run python -m kodalo.ui                 # window
uv run python -m kodalo.ui --no-window     # prints an address for a browser
uv run python -m kodalo.ui --dev           # Vite with hot reload; relaxes the CSP, development only
```

## Screens

| Screen | What it does |
| --- | --- |
| Brands | Welcome page for a first brand, then the list, an editor (Colors with contrast check, Fonts, Logo, Layout) and a live preview. Sub-menus manage Canvases, Palettes and Layouts. |
| Repositories | Add (folder or GitHub address, checked first), view and remove repositories; `Refresh with AI` for project files, frameworks and README; documents and files not read are shown. |
| Studio | Pick a repository, then the steps for one post: Focus, Ideas, Copy, Design, and export or post to Instagram. |
| Settings | GitHub access, Logs, AI (connections, models per job, history and usage), Platforms (hashtags, designer switches, Instagram connection) and Appearance (theme). |
| About | The product, its version, and a button that runs the `doctor` checks. |

## Decisions

- **Draft, then save.** Editors (brands, copy, settings forms) keep a draft: nothing is written until Save, and leaving with unsaved changes asks *Discard changes* or *Keep editing* (`useUnsavedGuard` and `useSavedValues` in `src/libs/unsaved.js`).
- **Only the open page is mounted** (`App.jsx`), so leaving a page drops its state and coming back reloads it from the server. No shared client cache.
- **AI always asks first.** Every AI action calls a `.../plan` route, shows the model and expected tokens in a confirmation panel, and only on `Proceed` sends. While it works, an overlay blocks clicks (a CSS-only animated robot, stopped for reduced motion).
- **Finished tasks notify.** Repository, Studio and settings tasks raise a Windows notification when they finish or fail (`notifying()` in `api.js`); it never fails the task.
- **Built-in items are read-only** (palettes, layouts, canvases); one in use cannot be deleted. Changing a list tells the brand editor to reload.
- **Post ideas** (`Next with AI` on Focus): one request with the saved README analysis for the chosen tool, feature, use case or capability, returning a strategy, three angles with three hooks each and the configured number of ideas (5 by default). Claims are kept only when their quote was sent. `Refresh with AI` adds new ideas to the saved ones, and an idea is flagged *Posted* after posting or when you say so after an export. The prompt is `src/kodalo/core/ai/prompts/marketing/marketing-strategist.SKILL.md`.
- **Theme** is read once at launch (`src/libs/theme.js`) and applied as `data-theme` and to the Fluent components (`src/libs/fluent.js`).

### The preview

`preview.jsx` draws sample slides (cover, content, code, quote, call to action) from the draft brand. It sets colors, fonts and sizes as CSS custom properties with `style.setProperty`, which Cornea's content security policy allows (an inline `style` attribute would not be). Sizes are in canvas pixels and scale with the container, so slides keep the chosen canvas's proportions. `src/libs/brand.js` maps brand data to those variables; the final slide renderer reads the same fields.

## Dependencies and conventions

- **Runtime:** React and React DOM, plus **Fluent UI Web Components** (`@fluentui/web-components`) for buttons, text and number fields and switches. They are registered once in `src/libs/fluent.js` and wrapped for React in `src/components/controls.jsx`, since a custom element keeps its value as a property and reports changes with DOM events. Tabs, navigation, selects and the colour picker are native elements styled with CSS.
- **Icons:** Bootstrap Icons only (`<i className="bi bi-..." aria-hidden="true" />`), imported in `styles/fonts.css`; icon-only controls get a label and a title.
- **Fonts** come from `@fontsource` packages (SIL OFL, latin subset, weights 400, 600, 700), imported in `src/styles/fonts.css`. They are dev dependencies because Vite copies the files into `dist`. The font list is in `kodalo.core.brands.brand.fonts`.
- **Rules:** plain JavaScript with function components and hooks, no TypeScript. Calls to Python live only in `src/libs/api.js`; a failed call is shown to the user. No `dangerouslySetInnerHTML`, `innerHTML` or `eval`, and no inline scripts or styles (Cornea's CSP forbids them), so styles live in CSS files.
- **Tooling:** Vite, Vitest with Testing Library and `vitest-axe`, ESLint (with `jsx-a11y` and security plugins) and Prettier. Node's version is in `src/kodalo/ui/ui/.nvmrc`.

## Tests and packaging

`npm run lint`, `npm test` and `npm run build` run in CI. Tests do not register the Fluent elements; `src/testing.js` has a fake API and helpers to type into them. The Python tests in `tests/ui/` replace Cornea's `Shell`, so no window opens. In `tests/ui/integration/` a Windows-only test starts the real server without a window (it needs a built `dist`) and another starts the built `kodalo-ui.exe`.

The window is not part of the Python package. Users get it from the Windows installer, which freezes `dist` into the build (`installer/pyinstaller/ui.spec`) and needs no Node; see [packaging](packaging.md). The window icon is `src/kodalo/ui/ui/public/icon.png`, and the app id, title and version are constants at the top of `kodalo/ui/app.py`.
