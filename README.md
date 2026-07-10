# `mysk`

Manage and deploy agent skills.

**Usage**:

```console
$ mysk [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--version`: Show the installed version and exit.
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `import`: Import a skill from a GitHub URL or local...
* `deploy`: Deploy skills to selected Deployment Targets.
* `cleanup`: Remove deprecated skills from all...
* `delete`: Delete a skill from the Skill Library and...
* `library`: Print the Skill Library filepath.
* `list`: List all skills and where they are deployed.
* `mark`: Interactively set a marking on one or more...
* `refresh`: Refresh an imported skill from its...
* `undeploy`: Remove deployed skills from selected...

## `mysk import`

Import a skill from a GitHub URL or local path into the Skill Library.

**Usage**:

```console
$ mysk import [OPTIONS] URL COMMAND [ARGS]...
```

**Arguments**:

* `URL`: GitHub URL or local path of the skill directory.  [required]

**Options**:

* `--rename TEXT`: Import the skill under a different local name.
* `--help`: Show this message and exit.

## `mysk deploy`

Deploy skills to selected Deployment Targets.

**Usage**:

```console
$ mysk deploy [OPTIONS] [SKILL] COMMAND [ARGS]...
```

**Arguments**:

* `[SKILL]`: Name of a single skill to deploy.

**Options**:

* `--overwrite`: Replace non-symlink directories at collision paths.
* `--agents TEXT`: Comma-separated agent names; defaults to all found.
* `--bulk TEXT`: Comma-separated skill names to deploy; skips the skill prompt.
* `--all`: Deploy every skill without prompting; skips the skill prompt.
* `--yes`: Skip confirmation before replacing a real directory.
* `--help`: Show this message and exit.

## `mysk cleanup`

Remove deprecated skills from all Deployment Targets.

**Usage**:

```console
$ mysk cleanup [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--bulk TEXT`: Comma-separated deprecated skill names to clean up; skips the picker.
* `--all`: Clean up every deprecated skill without prompting; skips the picker.
* `--yes`: Skip confirmation prompt.
* `--help`: Show this message and exit.

## `mysk delete`

Delete a skill from the Skill Library and all Deployment Targets.

**Usage**:

```console
$ mysk delete [OPTIONS] [NAME] COMMAND [ARGS]...
```

**Arguments**:

* `[NAME]`: Name of the skill to delete.

**Options**:

* `--bulk TEXT`: Comma-separated skill names to delete; skips the picker.
* `--all`: Delete every skill in the Skill Library without prompting.
* `--yes`: Skip confirmation prompt.
* `--help`: Show this message and exit.

## `mysk library`

Print the Skill Library filepath.

**Usage**:

```console
$ mysk library [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

## `mysk list`

List all skills and where they are deployed.

**Usage**:

```console
$ mysk list [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--upstream-urls`: Show each skill&#x27;s upstream source URL instead of a yes/no column.
* `--help`: Show this message and exit.

## `mysk mark`

Interactively set a marking on one or more skills.

**Usage**:

```console
$ mysk mark [OPTIONS] [SKILL_NAME] COMMAND [ARGS]...
```

**Arguments**:

* `[SKILL_NAME]`: Name of the skill to mark.

**Options**:

* `--bulk TEXT`: Comma-separated skill names to mark; skips the picker.
* `--all`: Mark every skill in the Skill Library.
* `--key TEXT`: Marking to set (status, modified).
* `--value TEXT`: Value for the marking.
* `--help`: Show this message and exit.

## `mysk refresh`

Refresh an imported skill from its upstream source URL.

**Usage**:

```console
$ mysk refresh [OPTIONS] [NAME] COMMAND [ARGS]...
```

**Arguments**:

* `[NAME]`: Name of the skill to refresh.

**Options**:

* `--bulk TEXT`: Comma-separated skill names to refresh; skips the picker.
* `--all`: Refresh all imported skills.
* `--yes`: Skip confirmation prompt.
* `--help`: Show this message and exit.

## `mysk undeploy`

Remove deployed skills from selected Deployment Targets.

**Usage**:

```console
$ mysk undeploy [OPTIONS] [SKILL] COMMAND [ARGS]...
```

**Arguments**:

* `[SKILL]`: Name of a single skill to undeploy.

**Options**:

* `--agents TEXT`: Comma-separated agent names; defaults to all found.
* `--bulk TEXT`: Comma-separated skill names to undeploy; skips the skill prompt.
* `--all`: Undeploy every skill without prompting; skips the skill prompt.
* `--help`: Show this message and exit.
