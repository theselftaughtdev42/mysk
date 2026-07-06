"""Command to remove deployed skills from selected Deployment Targets."""

from collections.abc import Sequence
from pathlib import Path

import questionary
import typer

from mysk.io.deploy import remove_skill
from mysk.io.skills import InstalledSkill, load_skills, skill_library
from mysk.io.targets import Target, discover_targets, is_deployed
from mysk.output import Output
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    resolve_skill_selection,
)

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def _not_deployed(
    result: InstalledSkill,
    targets: Sequence[Target],
    library: Path,
) -> str | None:
    if any(is_deployed(t, result.skill, library) for t in targets):
        return None
    return "not deployed"


@app.callback()
def undeploy(
    skill: str | None = typer.Argument(
        None, help="Name of a single skill to undeploy."
    ),
    *,
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated agent names to target; skips the target prompt.",
    ),
    bulk: str | None = typer.Option(
        None,
        "--bulk",
        help="Comma-separated skill names to undeploy; skips the skill prompt.",
    ),
    select_all: bool = typer.Option(
        False,
        "--all",
        help="Undeploy every skill without prompting; skips the skill prompt.",
    ),
) -> None:
    """Remove deployed skills from selected Deployment Targets."""
    # discover the available Deployment Targets
    targets = discover_targets()

    # load skills from the Skill Library
    library = skill_library()
    deployable, _ = load_skills(library)

    # resolve the Skill Selection from CLI flags
    try:
        selected_skills = resolve_skill_selection(
            skill=skill,
            bulk=bulk,
            select_all=select_all,
            eligible=deployable,
        )
    except SkillSelectionError as exc:
        out.error(str(exc))
        raise typer.Exit(1) from None

    # resolve the Deployment Targets from --agents or an interactive prompt
    if agents is not None:
        names = {n.strip() for n in agents.split(",")}
        known = {t.name for t in targets}
        unknown = names - known
        if unknown:
            out.error(f"Unknown agent(s): {', '.join(sorted(unknown))}")
            raise typer.Exit(1)
        selected_targets = [t for t in targets if t.name in names]
    else:
        selected_targets = questionary.checkbox(
            "Select deployment targets:\n",
            choices=[questionary.Choice(t.label(), value=t) for t in targets],
        ).ask()

    if not selected_targets:
        out.note("Nothing selected.")
        raise typer.Exit(0)

    # fall back to an interactive Skill Selection when no flag picked one
    if selected_skills is None:
        skill_choices = build_skill_choices(
            deployable,
            relevance=lambda r: _not_deployed(r, selected_targets, library),
        )
        if all(choice.disabled for choice in skill_choices):
            out.note("No skills deployed to the selected targets.")
            raise typer.Exit(0)
        selected_skills = questionary.checkbox(
            "Select skills to undeploy:\n",
            choices=skill_choices,
        ).ask()

    if not selected_skills:
        out.note("Nothing selected.")
        raise typer.Exit(0)

    # remove each selected skill from each target
    out.info(
        f"undeploying {len(selected_skills)} skill(s) from "
        f"{len(selected_targets)} target(s)"
    )
    for target in selected_targets:
        out.product(f"\n{target.name}:", raw=True)
        for skill_result in selected_skills:
            target_path = target.path / skill_result.skill.name
            result = remove_skill(target_path, skill_library_path=library)
            line = f"  {skill_result.skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            out.product(line, raw=True)
