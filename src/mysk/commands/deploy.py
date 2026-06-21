import sys

import questionary
import typer
from rich import print as rprint

from mysk.io.deploy import reconcile_skill
from mysk.io.skills import load_skills
from mysk.io.source_repo import find_source_repo
from mysk.io.targets import discover_targets


def deploy(
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Replace non-symlink directories at collision paths."
    ),
) -> None:
    """Deploy skills to selected Deployment Targets."""
    repo = find_source_repo()
    if repo is None:
        rprint("[red]Cannot find the mysk source repo.[/red]", file=sys.stderr)
        raise typer.Exit(1)

    targets = discover_targets()
    selected_targets = questionary.checkbox(
        "Select deployment targets:\n",
        choices=[questionary.Choice(t.label(), value=t) for t in targets],
    ).ask()

    if not selected_targets:
        print("Nothing selected.")
        raise typer.Exit(0)

    skills = load_skills(repo / "skills")
    deployable = [r for r in skills if r.skill and r.skill.mysk]

    selected_skills = questionary.checkbox(
        "Select skills to deploy:\n",
        choices=[
            questionary.Choice(f"{r.skill.name} ({r.skill.mysk.state.value})", value=r)
            for r in deployable
        ],
    ).ask()

    if not selected_skills:
        print("Nothing selected.")
        raise typer.Exit(0)

    for target in selected_targets:
        print(f"\n{target.name}:")
        for skill_result in selected_skills:
            skill = skill_result.skill
            source_dir = skill_result.path.parent
            target_path = target.path / skill.name
            result = reconcile_skill(source_dir, target_path, overwrite=overwrite)
            line = f"  {skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            print(line)
