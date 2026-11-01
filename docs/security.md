# Security

How the UI window and its API protect requests. To report a vulnerability, see [SECURITY.md](../SECURITY.md).

## Under the UI window

Cornea's `SecurityMiddleware` guards every mounted route, so the API adds no token of its own:

- the `Host` must be on the allow-list (the bound `127.0.0.1:<port>` only)
- state-changing requests (POST, PUT, PATCH, DELETE) must carry a matching `Origin`
- a one-time start-up token is exchanged for an `HttpOnly`, `SameSite=Strict` session cookie
- responses carry a strict content security policy and other protective headers

`kodalo.ui` therefore mounts the routes without any token of its own. The API has no standalone mode: it is never started on its own, has no API key and no settings file, and must not be exposed any other way.

The API itself still:

- limits request bodies to 1 MiB (logo uploads to 2 MB) and answers `413` above that
- serves no interactive docs
- never shows details of a `500`; they go to the log with the request ID
- sends its own protective headers when it is not hosted under Cornea (tests), and Cornea's own when it is

## Supply chain

Dependabot covers Python, npm and Actions. `audit.yml` checks locked dependencies weekly, dependency review blocks vulnerable additions, and the lock files are committed.

## Logo files

Brand logos are user-supplied files, so they are treated as untrusted. Only PNG and SVG are accepted, up to 2 MB, and every file is stored under a random name inside the data folder; a name or path from a request never reaches the file system. SVG files are refused when they contain scripts, event handlers, `foreignObject`, `use`, entities or a DOCTYPE, links that point outside the file, or styles that load anything from outside it. When a logo is served, the response carries `X-Content-Type-Options: nosniff` and a content security policy with `default-src 'none'` and `sandbox`, so it can be shown as an image but never run.
