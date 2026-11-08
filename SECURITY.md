# Security Policy

## Supported versions

Only the latest release receives security fixes.

## What is covered

Anything this project ships: the command line, the Windows window with the local API it runs on (the API is never started on its own), and the Windows installers published with each release. It also covers how Kodalo handles the credentials you give it (AI provider keys and Instagram tokens), the files it reads from your repositories, and the public address used for posting. Please report problems in Kodalo itself here, not in the dependencies it uses or in the AI provider and Instagram services; those go to their own projects. How the window, its API, secrets, AI calls and posting are protected is described in [docs/security.md](docs/security.md).

## Reporting a vulnerability

Please do **not** report vulnerabilities in public issues.

Use GitHub's private reporting: go to the **Security** tab of this repository and choose **Report a vulnerability**.

Include what you found, how to reproduce it, and the potential impact. You can expect an acknowledgement within a few days and updates as the fix progresses. Once a fix is released, we will credit you if you wish.
