# Security

How the UI window and its API protect requests. To report a vulnerability, see [SECURITY.md](../SECURITY.md).

## Under the UI window

Cornea's `SecurityMiddleware` guards every mounted route, so the API adds no token of its own:

- the `Host` must be on the allow-list (the bound `127.0.0.1:<port>` only)
- state-changing requests (POST, PUT, PATCH, DELETE) must carry a matching `Origin`
- a one-time start-up token is exchanged for an `HttpOnly`, `SameSite=Strict` session cookie
- responses carry a strict content security policy and other protective headers

AI provider API keys are kept in the system keychain (Windows Credential Manager) through `keyring`, never in the database, a file or a log. The database holds only a reference and the last four characters. The API accepts a key but never returns it, error messages never contain it or anything a provider sent back, and the command line takes it from a hidden prompt rather than an argument.

`kodalo.ui` therefore mounts the routes without any token of its own. The API has no standalone mode: it is never started on its own, has no API key and no settings file, and must not be exposed any other way.

The API itself still:

- limits request bodies to 1 MiB (logo uploads to 2 MB) and answers `413` above that
- serves no interactive docs
- never shows details of a `500`; they go to the log with the request ID
- sends its own protective headers when it is not hosted under Cornea (tests), and Cornea's own when it is

## AI parser step

`Refresh with AI` (and `studio read --refresh-with-ai`) sends the first 1.5 KB of up to five top-level project files that no parser config covers to the default AI provider. Lines containing `token`, `secret`, `password`, `api key`, `authorization` or `credential` are removed first, files named like secrets are never sent, and nothing is sent until the user approves the shown token estimate. The answer must be JSON; each config is checked against the config schema (data only, never code) and tried on the real file before it is saved to the `parsers` folder. Provider errors never include the key or the provider's reply.

## Claude Code as a provider

Kodalo runs `claude -p` as a plain text model: from an empty temporary folder (so no project instructions are read), with no tools, MCP servers, plugins, skills or saved session, and with Kodalo's own instructions in place of Claude Code's. This keeps your repositories and settings out of the call and keeps its tokens close to what Kodalo sends (a call went from about 37,000 to about 1,700 tokens). `--bare` is not used because it needs an API key instead of your sign-in.

## AI history

Every AI call is recorded locally (date, title, purpose, connection, model, tokens and status). The text of the prompt and the answer is kept only when `Keep the text of prompts and answers` is on, which is off by default; the text is what was sent to the provider, so it holds package and file names and the start of project files with secret-looking lines removed, never keys. Entries older than the retention period (90 days by default) are removed when the command line, the window or the API starts, and `Purge history` removes everything. History is stored in the local database, never sent anywhere.

## AI framework step

`Refresh with AI` (and `studio read --refresh-with-ai`), in the same single request as the project files above, sends only package names that no framework or tooling config covers (at most 80), the names of up to 40 top-level files and folders and up to 40 top-level names that look like configuration files to the default AI provider; file contents are never sent, names that look like secrets are left out, and nothing is sent until the user approves the shown token estimate. The answer must be JSON; each entry is checked against the framework config schema (data only, never code) and must match something that was sent before it is saved to the `frameworks` folder (or the `tooling` folder for tools).

## Supply chain

Dependabot covers Python, npm and Actions. `audit.yml` checks locked dependencies weekly, dependency review blocks vulnerable additions, and the lock files are committed.

## Logo files

Brand logos are user-supplied files, so they are treated as untrusted. Only PNG and SVG are accepted, up to 2 MB, and every file is stored under a random name inside the data folder; a name or path from a request never reaches the file system. SVG files are refused when they contain scripts, event handlers, `foreignObject`, `use`, entities or a DOCTYPE, links that point outside the file, or styles that load anything from outside it. When a logo is served, the response carries `X-Content-Type-Options: nosniff` and a content security policy with `default-src 'none'` and `sandbox`, so it can be shown as an image but never run.
