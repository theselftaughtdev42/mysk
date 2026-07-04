"""Command to deploy skills to selected Deployment Targets."""

from collections.abc import Sequence
from pathlib import Path

import questionary
import typer

from mysk.console import console, err_console
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
    # discover the available Deployment Targets
    targets = discover_targets()

    # load deployable skills from the Skill Library
    library = skill_library()
    deployable, _ = load_skills(library)

    if not deployable:
        console.print("No skills in the Skill Library to deploy.", markup=False)
        raise typer.Exit(0)

    # resolve the Skill Selection from CLI flags
    try:
        selected_skills = resolve_skill_selection(
            skill=skill, bulk=bulk, select_all=select_all, eligible=deployable
        )
    except SkillSelectionError as exc:
        err_console.print(str(exc), markup=False)
        raise typer.Exit(1) from None

    # resolve the Deployment Targets from --agents or an interactive prompt
    if agents is not None:
        names = {n.strip() for n in agents.split(",")}
        known = {t.name for t in targets}
        unknown = names - known
        if unknown:
            err_console.print(
                f"Unknown agent(s): {', '.join(sorted(unknown))}", markup=False
            )
            raise typer.Exit(1)
        selected_targets = [t for t in targets if t.name in names]
    else:
        selected_targets = questionary.checkbox(
            "Select deployment targets:\n",
            choices=[questionary.Choice(t.label(), value=t) for t in targets],
        ).ask()

    if not selected_targets:
        console.print("Nothing selected.", markup=False)
        raise typer.Exit(0)

    # fall back to an interactive Skill Selection when no flag picked one
    if selected_skills is None:
        skill_choices = build_skill_choices(
            deployable,
            relevance=lambda r: _already_deployed(r, selected_targets),
        )
        if all(choice.disabled for choice in skill_choices):
            console.print(
                "All skills already deployed to selected target(s).", markup=False
            )
            raise typer.Exit(0)
        selected_skills = questionary.checkbox(
            "Select skills to deploy:\n",
            choices=skill_choices,
        ).ask()

    if not selected_skills:
        console.print("Nothing selected.", markup=False)
        raise typer.Exit(0)

    # deploy each selected skill to each target
    for target in selected_targets:
        console.print(f"\n{target.name}:", markup=False)
        created = _ensure_target_dir(target.path)
        if created:
            console.print(f"  Created {created}", markup=False)
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
                    console.print(
                        f"  {skill_result.skill.name}: skipped (declined)", markup=False
                    )
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
            console.print(line, markup=False)
