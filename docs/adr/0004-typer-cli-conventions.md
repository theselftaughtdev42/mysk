# Typer CLI conventions: Annotated parameters, module-owned sub-apps, shared Rich consoles for output

The CLI follows three Typer conventions. Parameters use the `Annotated` form. Each command group owns its own `typer.Typer()` instance. Output goes through two shared Rich consoles — one for stdout, one for stderr — not `typer.echo`, `typer.secho`, or module-level `rich.print`.


## Parameter declaration: Annotated

Use `Annotated[<type>, typer.Option(...)]` with a plain default, not `typer.Option(default, ...)` as the default value itself.

```python
# correct
def cmd(dry_run: Annotated[bool, typer.Option("--dry-run", help="...")] = False) -> None: ...

# wrong — old style, not idiomatic
def cmd(dry_run: bool = typer.Option(False, "--dry-run", help="...")) -> None: ...
```

The `Annotated` form cleanly separates the Python default from the CLI metadata, and is what Typer explicitly recommends ("prefer the Annotated version if possible").

## Sub-app ownership

Each command group owns its own `app = typer.Typer(...)` instance in its package `__init__.py`. The root `cli.py` composes groups via `app.add_typer(group.app, name="...")` — it does not create sub-apps itself.

```
commands/import_skill/__init__.py   ← defines import app, registers import commands
cli.py                              ← imports import_skill.app, calls app.add_typer(import_skill.app, name="import")
```

## Output

All command screen output goes through two bare, shared Rich consoles defined in `mysk/console.py`.

> **Amended by [ADR-0009](0009-two-channel-output-facade.md).** The two consoles are now internals owned by the `Output` facade (`mysk/output.py`), which command modules use instead of importing `mysk.console` directly. The "all output through the consoles" rule holds for **user-facing** output; **diagnostics** are a separate `logging`-based channel (off unless `MYSK_LOG_LEVEL` is set). The stream contract and markup discipline below are unchanged — the facade enforces them internally.

### Stream contract (semantic, not exit-code-based)

The stream a message lands on is decided by *what the message is*, independent of the command's exit code:

| Stream | Console | Carries |
|--------|---------|---------|
| stdout | `console` | the command's **product** (the `library` path, the `list` table, deploy/undeploy/cleanup per-target reports, `import` section rules and progress), **success** confirmations, and neutral **"nothing to do"** notices |
| stderr | `err_console` | **errors** (invalid input, failures, not-found, malformed frontmatter, collisions) and **warnings** (data-loss caveats such as delete's "local modifications will be lost") |

A message's stream is independent of its exit code: e.g. "Nothing selected." exits non-zero in some commands but still prints to **stdout** because it is a normal outcome, not a failure. This keeps stdout clean and pipeable — `cd "$(mysk library)"` never captures diagnostic text — and lets errors and warnings stay visible when stdout is redirected.

### Markup discipline

`console.print`/`err_console.print` parse `[...]` as Rich markup. Two rules keep dynamic content safe:

- **Styled messages** (those carrying `[red]`/`[dim]`/… markup): wrap every interpolated dynamic value (skill names, exception text, paths, marking values) in `rich.markup.escape`, so a value containing `[` is never mis-parsed.
- **Pure-data lines** that carry no styling (the `library` path): pass `markup=False` to bypass parsing entirely. The `library` path additionally uses `soft_wrap=True` so a long path is emitted verbatim rather than wrapped at the console width.

The root app already declares `rich_markup_mode="rich"`.

## Considered options

- **Keep `typer.echo`/`typer.secho`** — rejected: Typer's docs now say "you are much better off using Rich for this."
- **`print()` / module-level `rich.print` (`rprint`)** — rejected: the deciding factor is ergonomics and consistency.
- **Old-style `typer.Option()` as default** — rejected: the `Annotated` form is what Typer now explicitly recommends and is cleaner for type checkers.
- **One `typer.Typer()` in `cli.py` for all groups** — rejected: as the CLI grows, command group ownership becomes unclear. The module-owned pattern gives each group a clear home.

## Consequences

- New command parameters must use `Annotated[<type>, typer.Option(...)]` or `Annotated[<type>, typer.Argument(...)]`.
- New command groups must define their `app = typer.Typer(...)` in their package `__init__.py` and be composed in `cli.py` via `add_typer`.
- New command output uses the shared `console` (stdout) / `err_console` (stderr) from `mysk.console`, routed by the semantic stream contract above; `typer.echo`, `typer.secho`, and module-level `rich.print` are not introduced.
- Dynamic values in styled messages are wrapped in `rich.markup.escape`; pure-data lines use `markup=False`.
