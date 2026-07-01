"""Command to remove deprecated skills from all Deployment Targets."""

import typer

from mysk.domain.lifecycle import LifecycleState
from mysk.io.deploy import remove_skill
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def confirm(msg: str) -> bool:
    """Prompt the user with *msg* and return True if they confirmed."""
    return typer.confirm(msg)


@app.callback()
def cleanup() -> None:
    """Remove deprecated skills from all Deployment Targets."""
    library = skill_library()
    installed, _ = load_skills(library)
    deprecated = [r for r in installed if r.mysk.state == LifecycleState.DEPRECATED]

    if not deprecated:
        typer.echo("Nothing to clean up.")
        raise typer.Exit(0)

    targets = discover_targets()

    skill_names = ", ".join(r.skill.name for r in deprecated)
    target_names = ", ".join(t.name for t in targets)
    if not confirm(
        f"Remove {len(deprecated)} deprecated skill(s) ({skill_names}) "
        f"from {len(targets)} target(s) ({target_names})?"
    ):
        raise typer.Exit(0)

    for target in targets:
        typer.echo(f"\n{target.name}:")
        for skill_result in deprecated:
            target_path = target.path / skill_result.skill.name
            result = remove_skill(target_path, skill_library_path=library)
            line = f"  {skill_result.skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            typer.echo(line)
