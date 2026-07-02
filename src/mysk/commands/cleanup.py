"""Command to remove deprecated skills from all Deployment Targets."""

import questionary
import typer

from mysk.domain.lifecycle import LifecycleState
from mysk.io.deploy import remove_skill
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    confirm,
    resolve_skill_selection,
)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


@app.callback()
def cleanup(
    *,
    bulk: str | None = typer.Option(
        None,
        "--bulk",
        help="Comma-separated deprecated skill names to clean up; skips the picker.",
    ),
    select_all: bool = typer.Option(
        False,
        "--all",
        help="Clean up every deprecated skill without prompting; skips the picker.",
    ),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
) -> None:
    """Remove deprecated skills from all Deployment Targets."""
    library = skill_library()
    installed, _ = load_skills(library)
    deprecated = [r for r in installed if r.mysk.state == LifecycleState.DEPRECATED]

    if not deprecated:
        typer.echo("Nothing to clean up.")
        raise typer.Exit(0)

    try:
        selected_skills = resolve_skill_selection(
            skill=None, bulk=bulk, select_all=select_all, eligible=deprecated
        )
    except SkillSelectionError as exc:
        typer.echo(str(exc))
        raise typer.Exit(1) from None

    if selected_skills is None:
        skill_choices = build_skill_choices(deprecated, relevance=lambda _: None)
        selected_skills = questionary.checkbox(
            "Select skills to clean up:\n", choices=skill_choices
        ).ask()

    if not selected_skills:
        typer.echo("Nothing selected.")
        raise typer.Exit(0)

    targets = discover_targets()

    skill_names = ", ".join(r.skill.name for r in selected_skills)
    target_names = ", ".join(t.name for t in targets)
    if not confirm(
        f"Remove {len(selected_skills)} deprecated skill(s) ({skill_names}) "
        f"from {len(targets)} target(s) ({target_names})?",
        yes=yes,
    ):
        raise typer.Exit(0)

    for target in targets:
        typer.echo(f"\n{target.name}:")
        for skill_result in selected_skills:
            target_path = target.path / skill_result.skill.name
            result = remove_skill(target_path, skill_library_path=library)
            line = f"  {skill_result.skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            typer.echo(line)
