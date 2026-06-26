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

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)

_SELECTABLE_STATES = [
    LifecycleState.ACTIVE,
    LifecycleState.EXPERIMENTAL,
    LifecycleState.DEPRECATED,
]

_VALID_KEYS = ["status", "modified"]


def set_skill_modified(skill_path: Path, value: bool) -> None:
    text = skill_path.read_text()
    data, body = frontmatter.read(text)
    if not data.get("mysk", {}).get("source"):
        raise ValueError(
            "skill is self-authored; modified only applies to imported skills"
        )
    data["mysk"]["modified"] = value
    skill_path.write_text(frontmatter.write(data, body))


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


def _apply_marking(skill_path: Path, value: LifecycleState | bool) -> str | None:
    if isinstance(value, LifecycleState):
        set_skill_lifecycle(skill_path, value)
        return None
    try:
        set_skill_modified(skill_path, value)
        return None
    except ValueError:
        name = escape(skill_path.parent.name)
        return f"[yellow]{name} is self-authored — skipping.[/yellow]"


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
    results = load_skills(skills_root)

    if skill_name is not None and key is not None and value is not None:
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
        warning = _apply_marking(match.path, resolved)
        if warning:
            rprint(warning, file=sys.stderr)
            raise typer.Exit(1)
        display_value = str(resolved) if key == "modified" else value.lower()
        rprint(
            f"[green]Marked {escape(skill_name)}: "
            f"{escape(key)} = {escape(display_value)}.[/green]"
        )
        return

    migrated = [r.path for r in results if r.schema_error is None]

    if not migrated:
        rprint("[dim]No skills in the Skill Library to mark.[/dim]")
        raise typer.Exit(0)

    selected = _prompt_for_skills(migrated)
    if not selected:
        raise typer.Exit(0)
    chosen_key = _prompt_for_key()
    chosen_value = _prompt_for_value(chosen_key)
    for skill_path in selected:
        warning = _apply_marking(skill_path, chosen_value)
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
