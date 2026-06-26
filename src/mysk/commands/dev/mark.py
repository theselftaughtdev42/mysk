import sys
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich import print as rprint
from rich.markup import escape

from mysk.domain import LifecycleState
from mysk.io import frontmatter
from mysk.io.skills import load_skills, skill_library

_SELECTABLE_STATES = [
    LifecycleState.ACTIVE,
    LifecycleState.EXPERIMENTAL,
    LifecycleState.DEPRECATED,
]


def set_skill_lifecycle(skill_path: Path, state: LifecycleState) -> None:
    text = skill_path.read_text()
    data, body = frontmatter.read(text)
    data["mysk"]["state"] = state.value
    skill_path.write_text(frontmatter.write(data, body))


def _choice_title(path: Path) -> str:
    data, _ = frontmatter.read(path.read_text())
    state = data.get("mysk", {}).get("state", "unknown")
    return f"{path.parent.name} ({state})"


def _prompt_for_skills(skills: list[Path]) -> list[Path]:
    chosen = questionary.checkbox(
        "Select skills to mark:\n",
        choices=[questionary.Choice(title=_choice_title(p), value=p) for p in skills],
    ).ask()
    return chosen or []


def _prompt_for_state() -> LifecycleState:
    return questionary.select(
        "Select lifecycle state:",
        choices=[
            questionary.Choice(title=s.value.capitalize(), value=s)
            for s in _SELECTABLE_STATES
        ],
    ).ask()


def dev_mark(
    skill_name: Annotated[
        str | None,
        typer.Argument(help="Name of the skill to mark."),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option("--status", help="Lifecycle state to set."),
    ] = None,
) -> None:
    """Interactively set the lifecycle state of a skill."""
    skills_root = skill_library()
    results = load_skills(skills_root)

    if skill_name is not None and status is not None:
        # find the first result matching the condition
        match = next((r for r in results if r.path.parent.name == skill_name), None)
        if match is None:
            rprint(
                f"[red]{escape(skill_name)} not found in the Skill Library.[/red]",
                file=sys.stderr,
            )
            raise typer.Exit(1)
        if match.schema_error is not None:
            rprint(
                f"[red]{escape(skill_name)} is not a valid skill"
                f" — {match.schema_error}."
                " Use mysk import to add skills to the library.[/red]",
                file=sys.stderr,
            )
            raise typer.Exit(1)
        try:
            state = LifecycleState(status.lower())
        except ValueError as e:
            rprint(f"[red]Unknown status: {escape(status)}[/red]", file=sys.stderr)
            raise typer.Exit(1) from e
        set_skill_lifecycle(match.path, state)
        rprint(f"[green]Marked {escape(skill_name)} as {state.value}.[/green]")
        return

    migrated = [r.path for r in results if r.schema_error is None]

    if not migrated:
        rprint("[dim]No skills in the Skill Library to mark.[/dim]")
        raise typer.Exit(0)

    selected = _prompt_for_skills(migrated)
    if not selected:
        raise typer.Exit(0)
    state = _prompt_for_state()
    for skill_path in selected:
        set_skill_lifecycle(skill_path, state)
    names = ", ".join(escape(p.parent.name) for p in selected)
    rprint(f"[green][bold]{names}[/bold] marked as [bold]{state.value}[/bold].[/green]")
