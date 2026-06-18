# my-skills
Agent skills I have either made myself (less likely) or politely stolen (more likely).

## Managing skills

### Migrate

Adopt existing skills into mysk management by adding a `mysk` block:

```sh
mysk dev migrate
```

Presents a checkbox of unmigrated skills. Use `--dry-run` to preview changes without writing files.

### Mark

Set the lifecycle state of one or more migrated skills:

```sh
mysk dev mark
```

Presents a checkbox of migrated skills, then a prompt for the new state: `Active`, `Experimental`, or `Deprecated`.

Non-interactive:

```sh
mysk dev mark <skill-name> --status experimental
```

Both commands must be run from inside the source repo.

## Developer setup

Install pre-commit hooks after cloning:

```sh
uv run pre-commit install
```

On each commit, four hooks run automatically:

1. **ruff-format** — reformats files in place
2. **ruff** — applies safe lint fixes
3. **pyrefly** — checks for type errors in `src/mysk`
4. **pytest** — runs the full test suite

If a hook modifies a file or finds an error, the commit aborts. Stage any formatting changes and re-commit.

CI also enforces an **80% coverage gate**. The pre-commit hook runs the suite but does not check the threshold.

To run all hooks manually without committing:

```sh
uv run pre-commit run --all-files
```
