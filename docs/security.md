# Security

How Kodalo protects requests, secrets and your data. To report a vulnerability, see [SECURITY.md](../SECURITY.md).

## The window and its API

The API is never started on its own: it only runs inside the window, under Cornea Shell, with no API key and no settings file. Cornea's `SecurityMiddleware` guards every route, so the API adds no token of its own:

- the `Host` must be on the allow-list (the bound `127.0.0.1:<port>` only)
- state-changing requests (POST, PUT, PATCH, DELETE) must carry a matching `Origin`
- a one-time start-up token is exchanged for an `HttpOnly`, `SameSite=Strict` session cookie
- responses carry a strict content security policy and other protective headers

The API also limits request bodies to 1 MiB (logo uploads to 2 MB, `413` above that), serves no interactive docs, and never shows the details of a `500`: they go to the log with the request ID.

## Secrets

AI provider API keys and the Instagram access token are kept in the system keychain (Windows Credential Manager) through `keyring`, never in the database, a file or a log. The database holds only a reference and the last four characters. The API and CLI accept a secret but never return it; the CLI reads it from a hidden prompt, not an argument; errors never contain it or anything a provider sent back. Kodalo never asks for an Instagram password, and the token goes only to `graph.facebook.com`.

## What is sent to AI

Nothing is sent until you approve the shown token estimate (`--yes` skips the question).

- **Repository analysis** (`Refresh with AI`): the first 1.5 KB of up to five top-level project files no parser covers, plus package names no config covers (at most 80), up to 40 top-level file names and up to 40 configuration-looking names. Lines containing `token`, `secret`, `password`, `api key`, `authorization` or `credential` are removed first, and files named like secrets are never sent.
- **README analysis, ideas, copy and design:** the saved analysis and documents for the chosen post, with secret-looking lines removed.
- **Answers** must be JSON. Parser, framework and tooling configs are data only, never code; each is checked against its schema and against what was sent before it is saved.
- **Claude Code** runs as a plain text model: from an empty temporary folder (no project instructions), with no tools, MCP servers, plugins, skills or saved session.

Every call is recorded locally (date, purpose, connection, model, tokens, status). The prompt and answer text is kept only when `Keep the text of prompts and answers` is on, which is off by default. Entries older than the retention period (90 days by default) are removed at start-up, and `Purge history` removes everything. History never leaves the local database.

## Posting to Instagram

Instagram fetches a post's pictures from a public address, so posting opens one briefly. Kodalo serves only that post's JPEGs from a random loopback port at `/kodalo/instagram/<name>.jpg?token=<random>` and answers `404` to anything else. A cloudflared quick tunnel makes the port reachable at a random `trycloudflare.com` address; both stop, and the pictures are deleted, as soon as the post finishes or fails. The server logs nothing, since the address carries the token. If this computer's DNS cannot resolve the new name, Kodalo asks Cloudflare's public DNS (`1.1.1.1`, over HTTPS) whether the name exists, sending only the random host name.

cloudflared is a third-party program, installed the first time you post: with winget when available, otherwise downloaded from Cloudflare's official GitHub release into Kodalo's data folder (no administrator rights) and refused unless its SHA-256 matches the digest GitHub lists. Slides become pictures through Microsoft Edge, run headless on local slide pages.

Exporting a post writes the pictures and `caption.txt` into a new folder inside a folder you chose. It never overwrites an existing folder, and it refuses network (UNC) paths. Nothing is public and nothing is sent to Instagram.

## Logo files

Logos are untrusted user files. Only PNG and SVG are accepted, up to 2 MB, stored under random names inside the data folder; a name or path from a request never reaches the file system. SVG files are refused when they contain scripts, event handlers, `foreignObject`, `use`, entities, a DOCTYPE, links pointing outside the file, or styles that load anything. A served logo carries `nosniff` and a policy with `default-src 'none'` and `sandbox`, so it shows as an image but never runs.

## Supply chain

Dependabot covers Python, npm and Actions. `audit.yml` checks locked dependencies weekly, dependency review blocks vulnerable additions, and the lock files are committed.
