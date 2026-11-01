# UI

The desktop window is hosted by [Cornea Shell](https://github.com/coldsofttech/CorneaShell) (`cornea-shell`). It runs on Windows only; the library, command line and API work on every system.

## Static files, dynamic app

Cornea serves the built files in `src/kodalo/ui/ui/dist`, but the page is a normal single-page app that talks to Python while it runs. `ui/` holds only the interface; everything dynamic lives in `kodalo.api` and `kodalo.core`:

- **Data:** `fetch('/api/v1/...')` calls the `kodalo.api` routes and gets JSON.
- **Native actions:** `POST /api/bridge/<action>` runs a Python function registered in `kodalo/ui/app.py`. `app_info` returns the app name and version for the About page. Cornea also provides file and folder pickers, opening links and platform info.
- **State:** lives in React in the page, and in Python behind the routes.

Cornea hosts the page and the API on one address, behind a start-up token that becomes a session cookie, a host and origin check, and strict response headers. See [security](security.md).

## Layout

```text
src/kodalo/ui/__main__.py   the `kodalo-ui` command: options, output, exit code
src/kodalo/ui/app.py        builds the Cornea shell: serves dist, mounts the API, registers actions
src/kodalo/ui/ui/           React + Vite (JavaScript): src/, index.html, package.json, tests
src/kodalo/ui/ui/dist/      build output, not committed; frozen into the Windows build
```

`app.py` only wires things together. It must not hold business logic, and `kodalo.api` and `kodalo.core` must never import `kodalo.ui`.

## Running it

```bash
uv sync
npm ci --prefix src/kodalo/ui/ui
npm run build --prefix src/kodalo/ui/ui
uv run python -m kodalo.ui                 # window
uv run python -m kodalo.ui --no-window     # prints an address for a browser
uv run python -m kodalo.ui --dev           # Vite with hot reload (needs Node)
```

`--dev` starts `npm run dev` through Cornea and relaxes the content security policy for Vite. Use it only while developing.

## Screens

- **Brands** is the first screen. With no brand yet it shows a welcome page (choose a starter palette, name the brand, or import a file). Otherwise it shows the list of brands, the editor and a live preview. The editor has four tabs: Colors (light and dark values, with a contrast check), Fonts, Logo and Layout. Edits are a draft: the preview follows every change, and nothing is written until you press Save (Discard throws the draft away, and leaving with unsaved changes asks first). Logo uploads and removals are the exception: the file is stored on the server, so they are saved straight away.
- **About** explains the product and has a button that runs the `doctor` checks (`GET /api/v1/doctor`) and shows the result.

## The preview

`preview.jsx` draws sample slides (cover, content, code, quote and call to action) from the draft brand. It sets the brand's colors, fonts and sizes as CSS custom properties on one element with `style.setProperty`, which Cornea's content security policy allows (an inline `style` attribute would not be). Sizes are written in canvas pixels and scaled with the slide's container width, so every slide keeps the proportions of the chosen canvas. `src/brand.js` holds the mapping from brand data to those variables; the slide designer that renders the final images must read the same fields the same way.

## Writing the frontend

- Plain JavaScript with JSX. Call Python only through `src/api.js`.
- Cornea's policy forbids inline scripts and styles, so put styles in CSS files.
- **Fluent UI Web Components** (`@fluentui/web-components`, MIT) provide the buttons, text and number fields and switches. They are registered once in `src/fluent.js` (which follows the system light or dark theme), and `src/components/controls.jsx` wraps them for React: a custom element keeps its value as a property and reports changes with DOM events. They add their styles through adopted style sheets, which the content security policy allows. Tabs, the navigation, selects and the colour picker are native elements styled with CSS.
- **Fonts** are bundled from the `@fontsource` packages (SIL Open Font License, latin subset, weights 400, 600 and 700), imported in `src/styles/fonts.css`. They are dev dependencies because Vite copies the files into `dist`. The list of font names is in `kodalo.core.brand.fonts`.
- `npm run lint`, `npm test` (Vitest, Testing Library and an accessibility check) and `npm run build` run in CI. Tests do not register the Fluent elements; `src/testing.js` has a fake API and helpers to "type" into them.

## Packaging

The window is not part of the Python package: `uv build` publishes only the core library and the command line. Users get the window from the Windows installer, which freezes `ui/dist` into the build (`installer/pyinstaller/ui.spec`) and needs no Node. The `kodalo-ui` command exists in that build; from the source tree you start it with `python -m kodalo.ui`.

The window and taskbar icon is `src/kodalo/ui/ui/public/icon.png` (copied into `dist` by the build), and the app id, title and version are constants at the top of `kodalo/ui/app.py`. The Windows setup and the standalone executables are described in [packaging](packaging.md).

## Tests

The Python tests in `tests/ui/` replace Cornea's `Shell`, so no window opens. In `tests/ui/integration/`, a Windows-only test starts the real server without a window and needs a built `dist`, and another starts the built `kodalo-ui.exe` (see [packaging](packaging.md)).
