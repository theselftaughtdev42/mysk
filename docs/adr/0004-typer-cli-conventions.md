# Typer CLI conventions: Annotated parameters, module-owned sub-apps, Rich/print for output

The CLI follows three Typer conventions. Parameters use the `Annotated` form. Each command group owns its own `typer.Typer()` instance. Output uses `print()` for plain text and `rich.print` for styled text — not `typer.echo` or `typer.secho`.

These align with Typer's current documented recommendations and were applied as a batch in mid-2026 after the initial scaffolding used older patterns.

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

| Situation | Use |
|-----------|-----|
| Plain informational output | `print()` |
| Styled output (markup, colour) | `from rich import print as rprint` |
| Stderr (plain) | `print(..., file=sys.stderr)` |
| Stderr (styled) | `rprint("[red]...[/red]", file=sys.stderr)` |

`typer.echo` and `typer.secho` are not used. Typer's own docs now position these as legacy, recommending Rich for styled output and the builtin `print` for simple cases. The root app already declares `rich_markup_mode="rich"`.

## Considered options

- **Keep `typer.echo`/`typer.secho`** — rejected: Typer's docs now say "you are much better off using Rich for this." Since `rich` is already a dependency and `rich_markup_mode="rich"` is set on the app, using `typer.secho` is inconsistent.
- **Old-style `typer.Option()` as default** — rejected: the `Annotated` form is what Typer now explicitly recommends and is cleaner for type checkers.
- **One `typer.Typer()` in `cli.py` for all groups** — rejected: as the CLI grows, command group ownership becomes unclear. The module-owned pattern gives each group a clear home.

## Consequences

- New command parameters must use `Annotated[<type>, typer.Option(...)]` or `Annotated[<type>, typer.Argument(...)]`.
- New command groups must define their `app = typer.Typer(...)` in their package `__init__.py` and be composed in `cli.py` via `add_typer`.
- `typer.echo` and `typer.secho` are not introduced for new output — use `print()` or `rprint()`.
