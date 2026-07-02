"""Command to deploy skills to selected Deployment Targets."""

from collections.abc import Sequence
from pathlib import Path

import questionary
import typer

from mysk.io.deploy import reconcile_skill
from mysk.io.skills import InstalledSkill, load_skills, skill_library
from mysk.io.targets import Target, discover_targets
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    confirm,
    resolve_skill_selection,
)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def _already_deployed(result: InstalledSkill, targets: Sequence[Target]) -> str | None:
    for target in targets:
        target_path = target.path / result.skill.name
        cleanly_deployed = (
            target_path.is_symlink() and target_path.resolve() == result.dir.resolve()
        )
        if not cleanly_deployed:
            return None
    return "already deployed"


def _ensure_target_dir(path: Path) -> str | None:
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)
        try:
            display = "~/" + str(path.relative_to(Path.home()))
        except ValueError:
            display = str(path)
        return display
    return None


@app.callback()
def deploy(
    skill: str | None = typer.Argument(None, help="Name of a single skill to deploy."),
    *,
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Replace non-symlink directories at collision paths."
    ),
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated agent names to target; skips the target prompt.",
    ),
    bulk: str | None = typer.Option(
        None,
        "--bulk",
        help="Comma-separated skill names to deploy; skips the skill prompt.",
    ),
    select_all: bool = typer.Option(
        False,
        "--all",
        help="Deploy every skill without prompting; skips the skill prompt.",
    ),
    yes: bool = typer.Option(
        False, "--yes", help="Skip confirmation before replacing a real directory."
    ),
) -> None:
    """Deploy skills to selected Deployment Targets."""
    targets = discover_targets()

    library = skill_library()
    deployable, _ = load_skills(library)

    if not deployable:
        typer.echo("No skills in the Skill Library to deploy.")
        raise typer.Exit(0)

    try:
        selected_skills = resolve_skill_selection(
            skill=skill, bulk=bulk, select_all=select_all, eligible=deployable
        )
    except SkillSelectionError as exc:
        typer.echo(str(exc))
        raise typer.Exit(1) from None

    if agents is not None:
        names = {n.strip() for n in agents.split(",")}
        known = {t.name for t in targets}
        unknown = names - known
        if unknown:
            typer.echo(f"Unknown agent(s): {', '.join(sorted(unknown))}")
            raise typer.Exit(1)
        selected_targets = [t for t in targets if t.name in names]
    else:
        selected_targets = questionary.checkbox(
            "Select deployment targets:\n",
            choices=[questionary.Choice(t.label(), value=t) for t in targets],
        ).ask()

    if not selected_targets:
        typer.echo("Nothing selected.")
        raise typer.Exit(0)

    if selected_skills is None:
        skill_choices = build_skill_choices(
            deployable,
            relevance=lambda r: _already_deployed(r, selected_targets),
        )
        if all(choice.disabled for choice in skill_choices):
            typer.echo("All skills already deployed to selected target(s).")
            raise typer.Exit(0)
        selected_skills = questionary.checkbox(
            "Select skills to deploy:\n",
            choices=skill_choices,
        ).ask()

    if not selected_skills:
        typer.echo("Nothing selected.")
        raise typer.Exit(0)

    for target in selected_targets:
        typer.echo(f"\n{target.name}:")
        created = _ensure_target_dir(target.path)
        if created:
            typer.echo(f"  Created {created}")
        for skill_result in selected_skills:
            target_path = target.path / skill_result.skill.name
            destroys_real_dir = (
                overwrite and target_path.exists() and not target_path.is_symlink()
            )
            if destroys_real_dir:
                message = (
                    f"'{target_path}' is a real directory, not a mysk symlink. "
                    "Replace it?"
                )
                if not confirm(message, yes=yes):
                    typer.echo(f"  {skill_result.skill.name}: skipped (declined)")
                    continue
            result = reconcile_skill(
                skill_result.dir,
                target_path,
                overwrite=overwrite,
                skill_library_path=library,
            )
            line = f"  {skill_result.skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            typer.echo(line)
