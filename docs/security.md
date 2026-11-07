# Security

How the UI window and its API protect requests. To report a vulnerability, see [SECURITY.md](../SECURITY.md).

## Under the UI window

Cornea's `SecurityMiddleware` guards every mounted route, so the API adds no token of its own:

- the `Host` must be on the allow-list (the bound `127.0.0.1:<port>` only)
- state-changing requests (POST, PUT, PATCH, DELETE) must carry a matching `Origin`
- a one-time start-up token is exchanged for an `HttpOnly`, `SameSite=Strict` session cookie
- responses carry a strict content security policy and other protective headers

AI provider API keys are kept in the system keychain (Windows Credential Manager) through `keyring`, never in the database, a file or a log. The database holds only a reference and the last four characters. The API accepts a key but never returns it, error messages never contain it or anything a provider sent back, and the command line takes it from a hidden prompt rather than an argument.

The Instagram access token is handled the same way: it is kept in the system keychain under `platform/instagram/token`, the settings hold only the account's name and ID and the last four characters of the token, the API never returns it, errors never contain it, and the command line takes it from a hidden prompt. Kodalo never asks for an Instagram password. The token is sent only to `graph.facebook.com`, to check it and to post. The Instagram account ID is not a secret and is kept in the settings.

`kodalo.ui` therefore mounts the routes without any token of its own. The API has no standalone mode: it is never started on its own, has no API key and no settings file, and must not be exposed any other way.

The API itself still:

- limits request bodies to 1 MiB (logo uploads to 2 MB) and answers `413` above that
- serves no interactive docs
- never shows details of a `500`; they go to the log with the request ID
- sends its own protective headers when it is not hosted under Cornea (tests), and Cornea's own when it is

## AI parser step

`Refresh with AI` (and `repositories add --refresh-with-ai`) sends the first 1.5 KB of up to five top-level project files that no parser config covers to the default AI provider. Lines containing `token`, `secret`, `password`, `api key`, `authorization` or `credential` are removed first, files named like secrets are never sent, and nothing is sent until the user approves the shown token estimate. The answer must be JSON; each config is checked against the config schema (data only, never code) and tried on the real file before it is saved to the `parsers` folder. Provider errors never include the key or the provider's reply.

## Claude Code as a provider

Kodalo runs `claude -p` as a plain text model: from an empty temporary folder (so no project instructions are read), with no tools, MCP servers, plugins, skills or saved session, and with Kodalo's own instructions in place of Claude Code's. This keeps your repositories and settings out of the call and keeps its tokens close to what Kodalo sends (a call went from about 37,000 to about 1,700 tokens). `--bare` is not used because it needs an API key instead of your sign-in.

## AI history

Every AI call is recorded locally (date, title, purpose, connection, model, tokens and status). The text of the prompt and the answer is kept only when `Keep the text of prompts and answers` is on, which is off by default; the text is what was sent to the provider, so it holds package and file names and the start of project files with secret-looking lines removed, never keys. Entries older than the retention period (90 days by default) are removed when the command line, the window or the API starts, and `Purge history` removes everything. History is stored in the local database, never sent anywhere.

## AI framework step

`Refresh with AI` (and `repositories add --refresh-with-ai`), in the same single request as the project files above, sends only package names that no framework or tooling config covers (at most 80), the names of up to 40 top-level files and folders and up to 40 top-level names that look like configuration files to the default AI provider; file contents are never sent, names that look like secrets are left out, and nothing is sent until the user approves the shown token estimate. The answer must be JSON; each entry is checked against the framework config schema (data only, never code) and must match something that was sent before it is saved to the `frameworks` folder (or the `tooling` folder for tools).

## Supply chain

Dependabot covers Python, npm and Actions. `audit.yml` checks locked dependencies weekly, dependency review blocks vulnerable additions, and the lock files are committed.

## Posting and the public address

Instagram fetches the pictures of a post from a public web address, so posting opens one for a moment. Kodalo serves only the post's JPEGs from a random local port on the loopback address, at `/kodalo/instagram/<name>.jpg?token=<random token>`, and answers 404 to anything else or to a wrong token. A cloudflared quick tunnel makes that port reachable at a random `trycloudflare.com` address, and both are stopped as soon as the post is done or fails; the pictures are deleted too. The server logs nothing, since the address carries the token. Before posting, Kodalo waits until the new address answers. When this computer's own DNS cannot look the new name up, it asks Cloudflare's public DNS (`1.1.1.1`, over HTTPS) only whether the name exists, sending the random host name and nothing else, because Instagram looks it up from its own servers.

cloudflared is a third-party program from Cloudflare. It is installed the first time you post: with winget when it is available, otherwise downloaded from Cloudflare's official GitHub release into Kodalo's data folder (no administrator rights) and refused unless its SHA-256 matches the digest GitHub lists for the file. Settings > Platforms > Instagram, the Post banner and About say so, and installing runs behind its own screen in the window or with `kodalo settings platforms instagram tunnel install`. Only Windows installs it for you; other systems are told how to. Slides are turned into pictures by Microsoft Edge, which comes with Windows, run headless on the local slide pages.

Exporting a post (`POST /api/v1/studio/repositories/{id}/design/export`, `kodalo studio design export`) writes the pictures and `caption.txt` into a new folder inside a folder the person chose. It never overwrites an existing folder and refuses network (UNC) paths and folders that do not exist. Nothing is public and nothing is sent to Instagram.

## Logo files

Brand logos are user-supplied files, so they are treated as untrusted. Only PNG and SVG are accepted, up to 2 MB, and every file is stored under a random name inside the data folder; a name or path from a request never reaches the file system. SVG files are refused when they contain scripts, event handlers, `foreignObject`, `use`, entities or a DOCTYPE, links that point outside the file, or styles that load anything from outside it. When a logo is served, the response carries `X-Content-Type-Options: nosniff` and a content security policy with `default-src 'none'` and `sandbox`, so it can be shown as an image but never run.
