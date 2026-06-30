"""Command to remove deployed skills from selected Deployment Targets."""

from typing import TYPE_CHECKING, cast

import questionary
import typer

from mysk.io.deploy import remove_skill
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets, is_deployed

if TYPE_CHECKING:
    from mysk.domain.skill import Skill

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


@app.callback()
def undeploy(
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated agent names to target; skips the target prompt.",
    ),
    skills: str | None = typer.Option(
        None,
        "--skills",
        help="Comma-separated skill names to undeploy; skips the skill prompt.",
    ),
    *,
    skills_all: bool = typer.Option(
        False,
        "--skills-all",
        help="Undeploy every deployed skill without prompting; skips the skill prompt.",
    ),
) -> None:
    """Remove deployed skills from selected Deployment Targets."""
    if skills_all and skills is not None:
        typer.echo("Cannot combine --skills-all with --skills.")
        raise typer.Exit(1)

    targets = discover_targets()

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

    library = skill_library()
    all_skills = load_skills(library)
    deployable = [r for r in all_skills if r.skill and r.skill.mysk]
    deployed = [
        r
        for r in deployable
        if r.skill is not None
        and any(is_deployed(t, r.skill) for t in selected_targets)
    ]

    if not deployed:
        typer.echo("No skills deployed to the selected targets.")
        raise typer.Exit(0)

    if skills_all:
        selected_skills = deployed
    elif skills is not None:
        names = {n.strip() for n in skills.split(",")}
        known = {r.skill.name for r in deployable if r.skill is not None}
        unknown = names - known
        if unknown:
            typer.echo(f"Unknown skill(s): {', '.join(sorted(unknown))}")
            raise typer.Exit(1)
        selected_skills = [
            r for r in deployable if r.skill is not None and r.skill.name in names
        ]
    else:
        selected_skills = questionary.checkbox(
            "Select skills to undeploy:\n",
            choices=[
                questionary.Choice(
                    f"{r.skill.name} ({r.skill.mysk.state.value})", value=r
                )
                for r in deployed
                if r.skill is not None and r.skill.mysk is not None
            ],
        ).ask()

    if not selected_skills:
        typer.echo("Nothing selected.")
        raise typer.Exit(0)

    for target in selected_targets:
        typer.echo(f"\n{target.name}:")
        for skill_result in selected_skills:
            skill = cast("Skill", skill_result.skill)
            target_path = target.path / skill.name
            result = remove_skill(target_path, skill_library_path=library)
            line = f"  {skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            typer.echo(line)
