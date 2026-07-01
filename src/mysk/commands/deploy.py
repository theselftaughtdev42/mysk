"""Command to deploy skills to selected Deployment Targets."""

from pathlib import Path

import questionary
import typer

from mysk.io.deploy import reconcile_skill
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


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
    *,
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Replace non-symlink directories at collision paths."
    ),
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated agent names to target; skips the target prompt.",
    ),
    skills: str | None = typer.Option(
        None,
        "--skills",
        help="Comma-separated skill names to deploy; skips the skill prompt.",
    ),
    skills_all: bool = typer.Option(
        False,
        "--skills-all",
        help="Deploy every skill without prompting; skips the skill prompt.",
    ),
) -> None:
    """Deploy skills to selected Deployment Targets."""
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
    deployable, _ = load_skills(library)

    if not deployable:
        typer.echo("No skills in the Skill Library to deploy.")
        raise typer.Exit(0)

    if skills_all:
        selected_skills = deployable
    elif skills is not None:
        names = {n.strip() for n in skills.split(",")}
        known = {r.skill.name for r in deployable}
        unknown = names - known
        if unknown:
            typer.echo(f"Unknown skill(s): {', '.join(sorted(unknown))}")
            raise typer.Exit(1)
        selected_skills = [r for r in deployable if r.skill.name in names]
    else:
        selected_skills = questionary.checkbox(
            "Select skills to deploy:\n",
            choices=[
                questionary.Choice(f"{r.skill.name} ({r.mysk.state.value})", value=r)
                for r in deployable
            ],
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
