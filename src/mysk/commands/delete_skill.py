"""Command to delete a skill from the Skill Library and all Deployment Targets."""

import shutil
from pathlib import Path

import questionary
import typer

from mysk.domain.naming import validate_skill_name
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets
from mysk.output import Output
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    confirm,
    resolve_skill_selection,
)

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def _delete_from_disk(name: str, skill_dir: Path, library: Path) -> None:
    for target in discover_targets():
        target_path = target.path / name
        # resolve() both sides: the Skill Library path may be a symlink
        # (e.g. /var → /private/var on macOS).
        if target_path.is_symlink() and target_path.resolve().is_relative_to(
            library.resolve()
        ):
            target_path.unlink()
    shutil.rmtree(skill_dir)


def _delete_unrecognized_by_name(name: str, library: Path, *, yes: bool) -> None:
    # Not a valid Skill Selection match (no SKILL.md, or malformed
    # frontmatter) — fall back to a raw directory-existence check so these
    # stay deletable by name. Never a "modified" mysk-owned skill: those
    # always resolve through resolve_skill_selection instead.
    # Guard before any path construction: "../.." and "" both pass
    # is_dir() and reach shutil.rmtree.
    try:
        validate_skill_name(name)
    except ValueError as exc:
        out.error(str(exc))
        raise typer.Exit(1) from None

    skill_dir = library / name
    if not skill_dir.is_dir():
        out.error(f"Skill '{name}' not found in the Skill Library.")
        raise typer.Exit(1)

    message = f"Delete '{name}' from the Skill Library and all Deployment Targets?"
    if not confirm(message, yes=yes):
        out.note("Aborted.")
        raise typer.Exit(0)

    _delete_from_disk(name, skill_dir, library)
    out.success(f"Deleted '{name}'.")


@app.callback()
def delete_skill(
    name: str | None = typer.Argument(None, help="Name of the skill to delete."),
    *,
    bulk: str | None = typer.Option(
        None,
        "--bulk",
        help="Comma-separated skill names to delete; skips the picker.",
    ),
    select_all: bool = typer.Option(
        False,
        "--all",
        help="Delete every skill in the Skill Library without prompting.",
    ),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
) -> None:
    """Delete a skill from the Skill Library and all Deployment Targets."""
    # load skills from the Skill Library
    library = skill_library()
    installed, _ = load_skills(library)

    # resolve the Skill Selection, falling back to a raw-name delete when a
    # single named skill does not load as a valid mysk skill
    try:
        selected = resolve_skill_selection(
            skill=name, bulk=bulk, select_all=select_all, eligible=installed
        )
    except SkillSelectionError as exc:
        if name is not None and bulk is None and not select_all:
            _delete_unrecognized_by_name(name, library, yes=yes)
            return
        out.error(str(exc))
        raise typer.Exit(1) from None

    # fall back to an interactive Skill Selection when no flag picked one
    if selected is None:
        skill_choices = build_skill_choices(installed, relevance=lambda _: None)
        selected = questionary.checkbox(
            "Select skills to delete:\n", choices=skill_choices
        ).ask()

    if not selected:
        out.note("Nothing selected.")
        raise typer.Exit(0)

    # warn about modified skills whose local changes will be lost
    modified = {r.skill.name for r in selected if r.mysk.provenance.modified}
    for skill_name in modified:
        out.warn(
            f"'{skill_name}' has local modifications that will be permanently lost."
        )

    # compose the confirmation prompt for the Skill Selection
    if len(selected) == 1:
        skill_name = selected[0].skill.name
        verb = "modified skill " if skill_name in modified else ""
        message = (
            f"Delete {verb}'{skill_name}' from the Skill Library "
            "and all Deployment Targets?"
        )
    else:
        names = ", ".join(r.skill.name for r in selected)
        message = (
            f"Delete {len(selected)} skill(s) ({names}) from the Skill Library "
            "and all Deployment Targets?"
        )

    if not confirm(message, yes=yes):
        out.note("Aborted.")
        raise typer.Exit(0)

    # delete each selected skill from the Skill Library and every target
    for skill_result in selected:
        _delete_from_disk(skill_result.skill.name, skill_result.dir, library)
        out.success(f"Deleted '{skill_result.skill.name}'.")
