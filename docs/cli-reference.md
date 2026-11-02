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
* `studio`: Start a post from a repository.

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
* `create`: Create a profile from a palette.
* `rename`: Rename a profile.
* `delete`: Delete a profile and its logo files.
* `default`: Make a profile the default.
* `duplicate`: Copy a profile, including its logo files.
* `check`: Check the contrast of a profile&#x27;s colors.
* `fonts`: List the fonts a profile can use (the font...
* `export`: Export a profile, with its logos, as JSON...
* `import`: Import a profile from a JSON file made by...
* `logo`: Set or remove a profile&#x27;s logo.
* `settings`: List and change the settings of a profile.
* `layout`: Manage layouts: named slide settings...
* `palette`: Manage palettes: named sets of brand...
* `canvas`: Manage canvases: named slide sizes that...

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

Create a profile from a palette.

**Usage**:

```console
$ kodalo brand create [OPTIONS] {name}
```

**Arguments**:

* `name`: Name of the new profile.  [required]

**Options**:

* `--palette <str>`: Palette name or id to start from. See: brand palette list  [default: midnight]
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

### `kodalo brand fonts`

List the fonts a profile can use (the font catalogue).

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

### `kodalo brand settings`

List and change the settings of a profile.

**Usage**:

```console
$ kodalo brand settings [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `set`: Change one setting.
* `list`: List the settings of a profile that...

#### `kodalo brand settings set`

Change one setting. Run `brand settings list NAME` to see the paths you can use.

**Usage**:

```console
$ kodalo brand settings set [OPTIONS] {name} {path} {value}
```

**Arguments**:

* `name`: Brand name or id.  [required]
* `path`: Setting, such as colors.primary.light.  [required]
* `value`: New value.  [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand settings list`

List the settings of a profile that `settings set` accepts, with their values.

**Usage**:

```console
$ kodalo brand settings list [OPTIONS] {name}
```

**Arguments**:

* `name`: Brand name or id.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo brand layout`

Manage layouts: named slide settings (canvas, margins, text, slide count) brands share.

**Usage**:

```console
$ kodalo brand layout [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List layouts: the built-in ones first,...
* `show`: Show every setting of a layout and the...
* `add`: Create a layout from another layout.
* `set`: Change one setting of a layout of your own.
* `settings`: List the settings that `layout set`...
* `rename`: Rename a layout of your own.
* `duplicate`: Copy a layout, built in or not, as a...
* `delete`: Delete a layout that no brand uses.
* `export`: Export a layout, with its canvas, as JSON...
* `import`: Import a layout from a JSON file made by...

#### `kodalo brand layout list`

List layouts: the built-in ones first, then yours.

**Usage**:

```console
$ kodalo brand layout list [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand layout show`

Show every setting of a layout and the brands that use it.

**Usage**:

```console
$ kodalo brand layout show [OPTIONS] {name}
```

**Arguments**:

* `name`: Layout name or id.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand layout add`

Create a layout from another layout. Change it afterwards with `layout set`.

**Usage**:

```console
$ kodalo brand layout add [OPTIONS] {name}
```

**Arguments**:

* `name`: Name of the new layout.  [required]

**Options**:

* `--from-layout <str>`: Start from this layout (default: Default).
* `--help`: Show this message and exit.

#### `kodalo brand layout set`

Change one setting of a layout of your own. Brands using it follow the change.

**Usage**:

```console
$ kodalo brand layout set [OPTIONS] {name} {path} {value}
```

**Arguments**:

* `name`: Layout name or id.  [required]
* `path`: Setting, such as margin_top or slides_count.  [required]
* `value`: New value. For canvas_id: a canvas name or id.  [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand layout settings`

List the settings that `layout set` accepts, with their values.

**Usage**:

```console
$ kodalo brand layout settings [OPTIONS] {name}
```

**Arguments**:

* `name`: Layout name or id.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand layout rename`

Rename a layout of your own.

**Usage**:

```console
$ kodalo brand layout rename [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Layout name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand layout duplicate`

Copy a layout, built in or not, as a layout of your own.

**Usage**:

```console
$ kodalo brand layout duplicate [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Layout name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand layout delete`

Delete a layout that no brand uses.

**Usage**:

```console
$ kodalo brand layout delete [OPTIONS] {name}
```

**Arguments**:

* `name`: Layout name or id.  [required]

**Options**:

* `-y, --yes`: Do not ask for confirmation.
* `--help`: Show this message and exit.

#### `kodalo brand layout export`

Export a layout, with its canvas, as JSON (to a file, or to the screen).

**Usage**:

```console
$ kodalo brand layout export [OPTIONS] {name}
```

**Arguments**:

* `name`: Layout name or id.  [required]

**Options**:

* `-o, --output <file>`: Write to a file.
* `--help`: Show this message and exit.

#### `kodalo brand layout import`

Import a layout from a JSON file made by `layout export`.

**Usage**:

```console
$ kodalo brand layout import [OPTIONS] {file}
```

**Arguments**:

* `file`: Exported JSON file.  [required]

**Options**:

* `--name <str>`: Name for the new layout.
* `--help`: Show this message and exit.

### `kodalo brand palette`

Manage palettes: named sets of brand colors that new brands start from.

**Usage**:

```console
$ kodalo brand palette [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List palettes: the built-in ones first,...
* `show`: Show every color of a palette.
* `add`: Create a palette from a brand&#x27;s colors or...
* `set`: Change one color of a palette of your own.
* `rename`: Rename a palette of your own.
* `duplicate`: Copy a palette, built in or not, as a...
* `delete`: Delete a palette of your own.
* `export`: Export a palette as JSON (to a file, or to...
* `import`: Import a palette from a JSON file made by...

#### `kodalo brand palette list`

List palettes: the built-in ones first, then yours.

**Usage**:

```console
$ kodalo brand palette list [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand palette show`

Show every color of a palette.

**Usage**:

```console
$ kodalo brand palette show [OPTIONS] {name}
```

**Arguments**:

* `name`: Palette name or id.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand palette add`

Create a palette from a brand&#x27;s colors or another palette (default: Midnight).

**Usage**:

```console
$ kodalo brand palette add [OPTIONS] {name}
```

**Arguments**:

* `name`: Name of the new palette.  [required]

**Options**:

* `--from-brand <str>`: Take the colors of this brand.
* `--from-palette <str>`: Start from this palette.
* `--help`: Show this message and exit.

#### `kodalo brand palette set`

Change one color of a palette of your own.

**Usage**:

```console
$ kodalo brand palette set [OPTIONS] {name} {path} {value}
```

**Arguments**:

* `name`: Palette name or id.  [required]
* `path`: Color, such as primary.light or text_alt.dark.  [required]
* `value`: New color, like #2563eb.  [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand palette rename`

Rename a palette of your own.

**Usage**:

```console
$ kodalo brand palette rename [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Palette name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand palette duplicate`

Copy a palette, built in or not, as a palette of your own.

**Usage**:

```console
$ kodalo brand palette duplicate [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Palette name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand palette delete`

Delete a palette of your own. Brands made from it keep their colors.

**Usage**:

```console
$ kodalo brand palette delete [OPTIONS] {name}
```

**Arguments**:

* `name`: Palette name or id.  [required]

**Options**:

* `-y, --yes`: Do not ask for confirmation.
* `--help`: Show this message and exit.

#### `kodalo brand palette export`

Export a palette as JSON (to a file, or to the screen).

**Usage**:

```console
$ kodalo brand palette export [OPTIONS] {name}
```

**Arguments**:

* `name`: Palette name or id.  [required]

**Options**:

* `-o, --output <file>`: Write to a file.
* `--help`: Show this message and exit.

#### `kodalo brand palette import`

Import a palette from a JSON file made by `palette export`.

**Usage**:

```console
$ kodalo brand palette import [OPTIONS] {file}
```

**Arguments**:

* `file`: Exported JSON file.  [required]

**Options**:

* `--name <str>`: Name for the new palette.
* `--help`: Show this message and exit.

### `kodalo brand canvas`

Manage canvases: named slide sizes that brand layouts reuse.

**Usage**:

```console
$ kodalo brand canvas [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List canvases: the built-in ones first,...
* `show`: Show one canvas and the brands that use it.
* `add`: Create a canvas.
* `edit`: Rename or resize a canvas.
* `duplicate`: Copy a canvas, built in or not, as a...
* `delete`: Delete a canvas that no brand uses.
* `export`: Export a canvas as JSON (to a file, or to...
* `import`: Import a canvas from a JSON file made by...

#### `kodalo brand canvas list`

List canvases: the built-in ones first, then yours.

**Usage**:

```console
$ kodalo brand canvas list [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand canvas show`

Show one canvas and the brands that use it.

**Usage**:

```console
$ kodalo brand canvas show [OPTIONS] {name}
```

**Arguments**:

* `name`: Canvas name or id.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

#### `kodalo brand canvas add`

Create a canvas.

**Usage**:

```console
$ kodalo brand canvas add [OPTIONS] {name} {width} {height}
```

**Arguments**:

* `name`: Name of the new canvas.  [required]
* `width`: Width in pixels (200 to 4000).  [required]
* `height`: Height in pixels (200 to 4000).  [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand canvas edit`

Rename or resize a canvas. Every brand that uses it follows the change.

**Usage**:

```console
$ kodalo brand canvas edit [OPTIONS] {name}
```

**Arguments**:

* `name`: Canvas name or id.  [required]

**Options**:

* `--name <str>`: New name.
* `--width <int>`: New width in pixels.
* `--height <int>`: New height in pixels.
* `--help`: Show this message and exit.

#### `kodalo brand canvas duplicate`

Copy a canvas, built in or not, as a canvas of your own.

**Usage**:

```console
$ kodalo brand canvas duplicate [OPTIONS] {name} {new_name}
```

**Arguments**:

* `name`: Canvas name or id.  [required]
* `new_name`: [required]

**Options**:

* `--help`: Show this message and exit.

#### `kodalo brand canvas delete`

Delete a canvas that no brand uses.

**Usage**:

```console
$ kodalo brand canvas delete [OPTIONS] {name}
```

**Arguments**:

* `name`: Canvas name or id.  [required]

**Options**:

* `-y, --yes`: Do not ask for confirmation.
* `--help`: Show this message and exit.

#### `kodalo brand canvas export`

Export a canvas as JSON (to a file, or to the screen).

**Usage**:

```console
$ kodalo brand canvas export [OPTIONS] {name}
```

**Arguments**:

* `name`: Canvas name or id.  [required]

**Options**:

* `-o, --output <file>`: Write to a file.
* `--help`: Show this message and exit.

#### `kodalo brand canvas import`

Import a canvas from a JSON file made by `canvas export`.

**Usage**:

```console
$ kodalo brand canvas import [OPTIONS] {file}
```

**Arguments**:

* `file`: Exported JSON file.  [required]

**Options**:

* `--name <str>`: Name for the new canvas.
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

## `kodalo studio`

Start a post from a repository.

**Usage**:

```console
$ kodalo studio [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `source`: Check a repository against the GitHub mode.
* `read`: Read a repository&#x27;s metadata, languages...
* `list`: List the repositories that were read before.
* `show`: Show a stored repository.

### `kodalo studio source`

Check a repository against the GitHub mode. Exits with 1 when it is not valid.

**Usage**:

```console
$ kodalo studio source [OPTIONS] {value}
```

**Arguments**:

* `value`: A folder (local_folder mode) or a GitHub repository address.  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo studio read`

Read a repository&#x27;s metadata, languages and structure, and store it.

**Usage**:

```console
$ kodalo studio read [OPTIONS] {value}
```

**Arguments**:

* `value`: A folder (local_folder mode) or a GitHub repository address.  [required]

**Options**:

* `--refresh`: Read again, even if stored.
* `--owner <str>`: Local folder: the owner (required once).
* `--repo <str>`: Local folder: the repository name.
* `--license <str>`: Local folder: the license, e.g. MIT.
* `--branch <str>`: Local folder: the default branch.
* `--description <str>`: Local folder: a short description.
* `--homepage <str>`: Local folder: the home page address.
* `--topic <str>`: Local folder: a topic; repeatable.
* `--private`: Local folder: it is private.
* `--fork`: Local folder: it is a fork.
* `--archived`: Local folder: it is archived.
* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo studio list`

List the repositories that were read before.

**Usage**:

```console
$ kodalo studio list [OPTIONS]
```

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.

### `kodalo studio show`

Show a stored repository.

**Usage**:

```console
$ kodalo studio show [OPTIONS] {repo_id}
```

**Arguments**:

* `repo_id`: Id of a stored repository (see studio list).  [required]

**Options**:

* `--json`: Output as JSON.
* `--help`: Show this message and exit.
