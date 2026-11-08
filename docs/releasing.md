# Releasing

How a release reaches PyPI, GitHub and the package managers. The PyPI trusted-publisher setup is in [development](development.md#releasing-to-pypi); the installers are described in [packaging](packaging.md).

## Making a release

1. Bump `__version__` in `src/<package>/__init__.py`, and move the `[Unreleased]` entries in `CHANGELOG.md` under a `## [x.y.z]` heading.
2. Merge that pull request, then publish a GitHub release tagged `v<version>`.
3. `release.yml` does the rest:

| Step | Result |
| --- | --- |
| Check | the tag must equal the version |
| Build | wheel and sdist (core library and command line only) |
| Publish | PyPI, through trusted publishing |
| Installers | Windows setups and zip; signed when a signing command is set |
| Release page | all files plus `SHA256SUMS.txt`; release notes from the `CHANGELOG.md` section, only if the release has no notes yet |
| Package managers | Scoop and winget pull requests, each only when switched on |

To check a download: `Get-FileHash <file>` on Windows and compare with the list.

## Build time

Starting targets, to be revisited after the first real runs and recorded here:

| Job | Target | `timeout-minutes` |
| --- | --- | --- |
| Windows installers | under 10 minutes | 20 on pull requests, 30 on releases |

A job that passes its timeout fails instead of hanging. uv and npm caches keep builds inside the targets.

## Signing

Signing is off by default. Without it, Windows shows SmartScreen warnings and may block the unsigned programs; winget still accepts the manifest.

To turn it on, set the repository variable `SIGN_COMMAND` to a command that signs one file, with `{file}` where the path goes. The build signs the executables first, then each `setup.exe`, so the files inside the installer are signed too. Any provider works, since the command is yours. Examples of what exists, without a recommendation:

- SignPath (free for qualifying open-source projects)
- Azure Trusted Signing (paid subscription)
- a certificate from a certificate authority, on a hardware token or in a cloud HSM

Secrets the command needs (a token, a certificate password) are added as repository secrets and passed to the `SIGN_COMMAND` step through `env` in `release.yml`, which is the one place to edit.

## Package managers

Each channel is off until you set its variable. Both need one secret, `PACKAGE_MANAGER_TOKEN`: a personal access token that can create repositories and open pull requests in the bucket, and that can fork `microsoft/winget-pkgs`. Updates are always pull requests; nothing is pushed to a default branch.

| Variable | Channel | Notes |
| --- | --- | --- |
| `PUBLISH_SCOOP=true` | Scoop (Windows) | `SCOOP_BUCKET_REPO`, default `<owner>/scoop-bucket` |
| `PUBLISH_WINGET=true` | winget (Windows) | `WINGET_IDENTIFIER`, for example `Publisher.Package`; `WINGET_INSTALLERS_REGEX` picks the setup (default: the command line's) |

Set them under Settings > Secrets and variables > Actions.

### Scoop

The workflow creates `<owner>/scoop-bucket` if needed and opens a pull request that adds or updates `bucket/<name>.json`, which points at the portable zip on the release and can update itself (`checkver` and `autoupdate`).

### winget

winget updates an existing package, so the first submission is manual:

1. Publish a release, so the setup is at a stable URL.
2. Run `wingetcreate new <url of the command line setup.exe>` (or `winget install wingetcreate` first) and answer the prompts. Choose the installer type `nullsoft`, silent switches `/S`, and the package identifier you will put in `WINGET_IDENTIFIER`.
3. Submit it. Microsoft's validation and review take from a few hours to several days; fix anything the bot reports on the pull request.
4. After it is merged, set `PUBLISH_WINGET=true`. From then on each release opens an update pull request.

## Installing

What to tell your users, once the channels are on:

| Channel | Install | Remove |
| --- | --- | --- |
| winget | `winget install <Identifier>` | `winget uninstall <Identifier>` |
| Scoop | `scoop bucket add <name> https://github.com/<owner>/scoop-bucket`, then `scoop install <name>` | `scoop uninstall <name>` |
| Windows setup | run `<name>-cli-<version>.setup.exe` (command line) or `<name>-<version>.setup.exe` (window) from the release page | Settings > Apps |
| PyPI (command line only) | `uv tool install <project>` or `pipx install <project>` | `uv tool uninstall <project>` |

## Before the first release

- Replace the window icon (`src/<ui package>/ui/public/icon.png`) with yours. Init has already generated new product GUIDs in `installer/windows/nsis/cli.nsi` and `ui.nsi`; keep them from now on.
- Pin the NSIS version you want in `installer/tools.toml`, and check the `choco` version exists.
- Decide on signing, and on which channels to switch on.
