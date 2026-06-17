from __future__ import annotations

import dataclasses
import difflib
from collections.abc import Callable
from pathlib import Path

import questionary
import typer

from mysk.domain import LifecycleState
from mysk.io import frontmatter
from mysk.io.source_repo import find_source_repo

Select = Callable[[list[Path]], list[Path]]


@dataclasses.dataclass(frozen=True)
class MigrationSummary:
    """Outcome of a migration run.

    ``upgraded`` are the skills that gained (or, under dry-run, would gain) a
    ``mysk`` block; ``already_compliant`` were owned beforehand; ``skipped`` are
    unmigrated skills the caller chose not to adopt. ``diffs`` holds the unified
    diff for each upgraded skill, so a dry-run can show exactly what would change.
    """

    upgraded: list[Path] = dataclasses.field(default_factory=list)
    already_compliant: list[Path] = dataclasses.field(default_factory=list)
    skipped: list[Path] = dataclasses.field(default_factory=list)
    diffs: dict[Path, str] = dataclasses.field(default_factory=dict)


def migrate_skills(
    skills_root: Path, select: Select, *, dry_run: bool = False
) -> MigrationSummary:
    """Adopt unmigrated skills under ``skills_root`` into mysk management.

    A skill is unmigrated when its frontmatter has no ``mysk`` block. The
    caller's ``select`` chooses which unmigrated skills to adopt; each chosen
    one gains a ``mysk`` block at ``init`` while every other key and the body
    are left exactly as they were. ``dry_run`` computes the same result and
    diffs without touching any file.
    """
    compliant: list[Path] = []
    unmigrated: list[Path] = []
    for path in sorted(skills_root.glob("*/SKILL.md")):
        (unmigrated if _is_unmigrated(path) else compliant).append(path)

    chosen = set(select(unmigrated))
    summary = MigrationSummary(already_compliant=compliant)
    for path in unmigrated:
        if path not in chosen:
            summary.skipped.append(path)
            continue
        before = path.read_text()
        after = _with_init_block(before)
        summary.upgraded.append(path)
        summary.diffs[path] = _diff(path, before, after)
        if not dry_run:
            path.write_text(after)
    return summary


def _with_init_block(text: str) -> str:
    data, body = frontmatter.read(text)
    data["mysk"] = {"state": LifecycleState.INIT.value}
    return frontmatter.write(data, body)


def _diff(path: Path, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def _is_unmigrated(path: Path) -> bool:
    data, _ = frontmatter.read(path.read_text())
    return "mysk" not in data


def _prompt_for_skills(unmigrated: list[Path]) -> list[Path]:
    if not unmigrated:
        return []
    chosen = questionary.checkbox(
        "Select skills to migrate (state: init):",
        choices=[questionary.Choice(title=p.parent.name, value=p) for p in unmigrated],
    ).ask()
    return chosen or []


def dev_migrate(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing any files."
    ),
) -> None:
    """Adopt unmigrated skills into mysk by adding a `mysk` block at state init."""
    repo = find_source_repo()
    if repo is None:
        typer.secho(
            "mysk dev migrate must be run from inside the mysk source repo.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    summary = migrate_skills(repo / "skills", _prompt_for_skills, dry_run=dry_run)

    if dry_run:
        for path in summary.upgraded:
            typer.echo(summary.diffs[path])

    verb = "would migrate" if dry_run else "migrated"
    typer.echo(
        f"{verb} {len(summary.upgraded)} · "
        f"already compliant {len(summary.already_compliant)} · "
        f"skipped {len(summary.skipped)}"
    )
