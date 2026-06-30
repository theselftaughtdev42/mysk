"""Command to delete a skill from the Skill Library and all Deployment Targets."""

import shutil
from pathlib import Path

import questionary
import typer

from mysk.domain.naming import validate_skill_name
from mysk.domain.skill import Skill
from mysk.io import frontmatter
from mysk.io.skills import skill_library
from mysk.io.targets import discover_targets

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def _is_modified(skill_dir: Path) -> bool:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return False
    try:
        data, _ = frontmatter.read(skill_md.read_text())
        skill = Skill.from_frontmatter(data)
    except (OSError, ValueError, KeyError):
        return False
    else:
        return skill.mysk is not None and skill.mysk.provenance.modified


@app.callback()
def delete_skill(
    name: str = typer.Argument(..., help="Name of the skill to delete."),
    *,
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
) -> None:
    """Delete a skill from the Skill Library and all Deployment Targets."""
    # Guard before any path construction: "../.." and "" both pass
    # is_dir() and reach shutil.rmtree.
    try:
        validate_skill_name(name)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from None

    library = skill_library()
    skill_dir = library / name

    if not skill_dir.is_dir():
        typer.echo(f"Skill '{name}' not found in the Skill Library.")
        raise typer.Exit(1)

    if not yes:
        if _is_modified(skill_dir):
            typer.echo(
                f"Warning: '{name}' has local modifications "
                "that will be permanently lost."
            )
            message = (
                f"Delete modified skill '{name}' from the Skill Library "
                "and all Deployment Targets?"
            )
        else:
            message = (
                f"Delete '{name}' from the Skill Library and all Deployment Targets?"
            )

        confirmed = questionary.confirm(message).ask()
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    targets = discover_targets()
    for target in targets:
        target_path = target.path / name
        # resolve() both sides: MYSK_SKILLS_DIR may be a symlink
        # (e.g. /var → /private/var on macOS).
        if target_path.is_symlink() and target_path.resolve().is_relative_to(
            library.resolve()
        ):
            target_path.unlink()

    shutil.rmtree(skill_dir)
    typer.echo(f"Deleted '{name}'.")
