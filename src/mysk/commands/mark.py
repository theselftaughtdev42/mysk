"""Command to interactively set markings (state, modified, etc) on skills."""

import sys
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich import print as rprint
from rich.markup import escape

from mysk.domain import LifecycleState, Skill
from mysk.io import frontmatter
from mysk.io.skills import load_skills, skill_library

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)

_SELECTABLE_STATES = [
    LifecycleState.ACTIVE,
    LifecycleState.EXPERIMENTAL,
    LifecycleState.DEPRECATED,
]

_VALID_KEYS = ["status", "modified"]


def set_skill_modified(skill_path: Path, *, value: bool) -> None:
    """Write the `modified` flag on an imported skill's SKILL.md."""
    text = skill_path.read_text()
    data, body = frontmatter.read(text)
    skill = Skill.from_frontmatter(data).with_modified(value=value)
    skill_path.write_text(frontmatter.write(skill.to_frontmatter(), body))


def set_skill_lifecycle(skill_path: Path, state: LifecycleState) -> None:
    """Write the lifecycle `state` on a skill's SKILL.md."""
    text = skill_path.read_text()
    data, body = frontmatter.read(text)
    skill = Skill.from_frontmatter(data).with_state(state)
    skill_path.write_text(frontmatter.write(skill.to_frontmatter(), body))


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


def _prompt_for_key() -> str:
    return questionary.select(
        "Select marking:",
        choices=[questionary.Choice(title=k, value=k) for k in _VALID_KEYS],
    ).ask()


def _prompt_for_value(key: str) -> LifecycleState | bool:
    if key == "status":
        return questionary.select(
            "Select value:",
            choices=[
                questionary.Choice(title=s.value, value=s) for s in _SELECTABLE_STATES
            ],
        ).ask()
    return questionary.select(
        "Select value:",
        choices=[
            questionary.Choice(title="true", value=True),
            questionary.Choice(title="false", value=False),
        ],
    ).ask()


def _apply_marking(skill_path: Path, *, value: LifecycleState | bool) -> str | None:
    if isinstance(value, LifecycleState):
        set_skill_lifecycle(skill_path, value)
        return None
    try:
        set_skill_modified(skill_path, value=value)
    except ValueError:
        name = escape(skill_path.parent.name)
        return f"[yellow]{name} is self-authored — skipping.[/yellow]"
    else:
        return None


@app.callback()
def mark_skill(
    skill_name: Annotated[
        str | None,
        typer.Argument(help="Name of the skill to mark."),
    ] = None,
    key: Annotated[
        str | None,
        typer.Option("--key", help="Marking to set (status, modified)."),
    ] = None,
    value: Annotated[
        str | None,
        typer.Option("--value", help="Value for the marking."),
    ] = None,
) -> None:
    """Interactively set a marking on one or more skills."""
    skills_root = skill_library()
    installed, errors = load_skills(skills_root)

    if skill_name is not None and key is not None and value is not None:
        installed_match = next((r for r in installed if r.dir.name == skill_name), None)
        if installed_match is None:
            error_match = next(
                (r for r in errors if r.path.parent.name == skill_name), None
            )
            if error_match is None:
                rprint(
                    f"[red]{escape(skill_name)} not found in the Skill Library.[/red]",
                    file=sys.stderr,
                )
            else:
                rprint(
                    f"[red]{escape(skill_name)} is not a valid skill"
                    f" — {error_match.schema_error}."
                    " Use mysk import to add skills to the library.[/red]",
                    file=sys.stderr,
                )
            raise typer.Exit(1)
        if key not in _VALID_KEYS:
            rprint(f"[red]Unknown key: {escape(key)}[/red]", file=sys.stderr)
            raise typer.Exit(1)
        if key == "status":
            try:
                resolved: LifecycleState | bool = LifecycleState(value.lower())
            except ValueError as e:
                rprint(f"[red]Unknown status: {escape(value)}[/red]", file=sys.stderr)
                raise typer.Exit(1) from e
        else:
            lower = value.lower()
            if lower not in ("true", "false"):
                rprint(
                    f"[red]Invalid value for modified: {escape(value)}"
                    " — must be true or false.[/red]",
                    file=sys.stderr,
                )
                raise typer.Exit(1)
            resolved = lower == "true"
        warning = _apply_marking(installed_match.skill_md, value=resolved)
        if warning:
            rprint(warning, file=sys.stderr)
            raise typer.Exit(1)
        display_value = str(resolved) if key == "modified" else value.lower()
        rprint(
            f"[green]Marked {escape(skill_name)}: "
            f"{escape(key)} = {escape(display_value)}.[/green]"
        )
        return

    skill_mds = [r.skill_md for r in installed]

    if not skill_mds:
        rprint("[dim]No skills in the Skill Library to mark.[/dim]")
        raise typer.Exit(0)

    selected = _prompt_for_skills(skill_mds)
    if not selected:
        raise typer.Exit(0)
    chosen_key = _prompt_for_key()
    chosen_value = _prompt_for_value(chosen_key)
    for skill_path in selected:
        warning = _apply_marking(skill_path, value=chosen_value)
        if warning:
            rprint(warning)
    names = ", ".join(escape(p.parent.name) for p in selected)
    display = (
        chosen_value.value
        if isinstance(chosen_value, LifecycleState)
        else str(chosen_value).lower()
    )
    rprint(
        f"[green][bold]{names}[/bold] marked: "
        f"{escape(chosen_key)}={escape(display)}.[/green]"
    )
