# `kodalo`

Example command line tool built on <span style="font-weight: bold">kodalo.core</span>.

**Usage**:

```console
$ kodalo [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `-V, --version`: Show the version and exit.
* `-v, --verbose`: Show extra detail.
* `-q, --quiet`: Only show errors.
* `--no-color`: Disable colored output.
* `--data-dir <directory>`: Folder for the database and logos. Default: %LOCALAPPDATA%/Kodalo.
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `doctor`: Diagnose the installation and the local data.
* `brand`: Manage brand profiles: colors, fonts, logo...
* `settings`: Change Kodalo&#x27;s settings.

## `kodalo doctor`

Diagnose the installation and the local data. Exits with 1 if a required check fails.

**Usage**:

```console
$ kodalo doctor [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

## `kodalo brand`

Manage brand profiles: colors, fonts, logo and layout.

**Usage**:

```console
$ kodalo brand [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List brand profiles.
* `show`: Show every setting of a profile.
* `create`: Create a profile from a starter palette.
* `rename`: Rename a profile.
* `delete`: Delete a profile and its logo files.
* `default`: Make a profile the default.
* `duplicate`: Copy a profile, including its logo files.
* `set`: Change one setting.
* `settings`: List the setting paths that `set` accepts.
* `check`: Check the contrast of a profile&#x27;s colors.
* `palettes`: List the starter palettes.
* `fonts`: List the fonts a profile can use.
* `export`: Export a profile, with its logos, as JSON...
* `import`: Import a profile from a JSON file made by...
* `logo`: Set or remove a profile&#x27;s logo.

### `kodalo brand list`

List brand profiles.

**Usage**:

```console
$ kodalo brand list [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo brand show`

Show every setting of a profile.

**Usage**:

```console
$ kodalo brand show [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo brand create`

Create a profile from a starter palette.

**Usage**:

```console
$ kodalo brand create [OPTIONS] {name}
```

**Arguments**:

* `name`: Name of the new profile.  [required]

**Options**:

* `--palette <str>`: Starter palette: midnight, paper or graphite.  [default: midnight]
* `--default`: Make it the default.
* `--help`: Show this message and exit.

### `kodalo brand rename`

Rename a profile.

**Usage**:

```console
$ kodalo brand rename [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Brand name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

### `kodalo brand delete`

Delete a profile and its logo files.

**Usage**:

```console
$ kodalo brand delete [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `-y, --yes`: Do not ask for confirmation.
* `--help`: Show this message and exit.

### `kodalo brand default`

Make a profile the default.

**Usage**:

```console
$ kodalo brand default [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `--help`: Show this message and exit.

### `kodalo brand duplicate`

Copy a profile, including its logo files.

**Usage**:

```console
$ kodalo brand duplicate [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Brand name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

### `kodalo brand set`

Change one setting. Run `brand settings NAME` to list the paths you can use.

**Usage**:

```console
$ kodalo brand set [OPTIONS] {name} {path} {value}
```

**Arguments**:

* `name`: Brand name or id.  [required]
* `path`: Setting, such as colors.primary.light.  [required]
* `value`: New value.  [required]

**Options**:

* `--help`: Show this message and exit.

### `kodalo brand settings`

List the setting paths that `set` accepts.

**Usage**:

```console
$ kodalo brand settings [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `--help`: Show this message and exit.

### `kodalo brand check`

Check the contrast of a profile&#x27;s colors.

**Usage**:

```console
$ kodalo brand check [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `--strict`: Exit with 1 if any check fails.
* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo brand palettes`

List the starter palettes.

**Usage**:

```console
$ kodalo brand palettes [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo brand fonts`

List the fonts a profile can use.

**Usage**:

```console
$ kodalo brand fonts [OPTIONS]
```

**Options**:

* `--system / --bundled`: Include installed fonts (default) or not.  [default: system]
* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo brand export`

Export a profile, with its logos, as JSON (to a file, or to the screen).

**Usage**:

```console
$ kodalo brand export [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `-o, --output <file>`: Write to a file.
* `--help`: Show this message and exit.

### `kodalo brand import`

Import a profile from a JSON file made by `export`.

**Usage**:

```console
$ kodalo brand import [OPTIONS] {file}
```

**Arguments**:

* `file`: Exported JSON file.  [required]

**Options**:

* `--name <str>`: Name for the new profile.
* `--help`: Show this message and exit.

### `kodalo brand logo`

Set or remove a profile&#x27;s logo.

**Usage**:

```console
$ kodalo brand logo [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `set`: Set a profile&#x27;s logo from a PNG or SVG file.
* `remove`: Remove a profile&#x27;s logo.

#### `kodalo brand logo set`

Set a profile&#x27;s logo from a PNG or SVG file.

**Usage**:

```console
$ kodalo brand logo set [OPTIONS] {name} {file}
```

**Arguments**:

* `name`: Brand name or id.  [required]
* `file`: PNG or SVG file.  [required]

**Options**:

* `--dark`: Use it as the dark-mode logo.
* `--help`: Show this message and exit.

#### `kodalo brand logo remove`

Remove a profile&#x27;s logo.

**Usage**:

```console
$ kodalo brand logo remove [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `--dark`: Remove the dark-mode logo.
* `--help`: Show this message and exit.

## `kodalo settings`

Change Kodalo&#x27;s settings.

**Usage**:

```console
$ kodalo settings [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `github`: Choose how Kodalo reaches GitHub: a local...

### `kodalo settings github`

Choose how Kodalo reaches GitHub: a local folder, the gh CLI or the web.

**Usage**:

```console
$ kodalo settings github [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `show`: Show the current GitHub connectivity setting.
* `set`: Choose the way to reach GitHub.
* `check`: Check that the chosen way works.

#### `kodalo settings github show`

Show the current GitHub connectivity setting.

**Usage**:

```console
$ kodalo settings github show [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo settings github set`

Choose the way to reach GitHub.

**Usage**:

```console
$ kodalo settings github set [OPTIONS] {mode}
```

**Arguments**:

* `mode`: One of: local_folder, gh_cli, web_fetch.  [required]

**Options**:

* `--folder <str>`: Folder holding your repositories (for local_folder).
* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo settings github check`

Check that the chosen way works. Exits with 1 when it does not.

**Usage**:

```console
$ kodalo settings github check [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.
