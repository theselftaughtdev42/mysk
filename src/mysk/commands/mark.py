"""Command to interactively set markings (state, modified, etc) on skills."""

from pathlib import Path
from typing import Annotated

import questionary
import typer

from mysk.domain import LifecycleState, Skill
from mysk.io import frontmatter
from mysk.io.skills import InstalledSkill, SkillLoadError, load_skills, skill_library
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
        return f"{skill_path.parent.name} is self-authored — skipping."
    else:
        return None


def _validate_key(key: str) -> None:
    if key not in _VALID_KEYS:
        out.error(f"Unknown key: {key}")
        raise typer.Exit(1)


def _resolve_value(key: str, value: str) -> LifecycleState | bool:
    if key == "status":
        try:
            return LifecycleState(value.lower())
        except ValueError as e:
            out.error(f"Unknown status: {value}")
            raise typer.Exit(1) from e
    lower = value.lower()
    if lower not in ("true", "false"):
        out.error(f"Invalid value for modified: {value} — must be true or false.")
        raise typer.Exit(1)
    return lower == "true"


def _report_selection_error(
    exc: SkillSelectionError,
    *,
    skill_name: str | None,
    bulk: str | None,
    select_all: bool,
    errors: list[SkillLoadError],
) -> None:
    if skill_name is None or bulk is not None or select_all:
        out.error(str(exc))
        return
    error_match = next((e for e in errors if e.path.parent.name == skill_name), None)
    if error_match is None:
        out.error(f"{skill_name} not found in the Skill Library.")
    else:
        out.error(
            f"{skill_name} is not a valid skill — {error_match.schema_error}."
            " Use mysk import to add skills to the library."
        )


def _resolve_selection(
    installed: list[InstalledSkill], selected: list[InstalledSkill] | None
) -> list[InstalledSkill]:
    if selected is not None:
        return selected
    if not installed:
        out.note("No skills in the Skill Library to mark.")
        raise typer.Exit(0)
    choices = build_skill_choices(installed, relevance=lambda _: None)
    chosen = questionary.checkbox("Select skills to mark:\n", choices=choices).ask()
    if not chosen:
        raise typer.Exit(0)
    return chosen


def _apply_and_report(
    selected: list[InstalledSkill],
    *,
    skill_name: str | None,
    chosen_key: str,
    chosen_value: LifecycleState | bool,
) -> None:
    # apply the marking to each selected skill, collecting warnings
    warnings = []
    for result in selected:
        warning = _apply_marking(result.skill_md, value=chosen_value)
        if warning:
            warnings.append(warning)

    # surface warnings — fatal in single-skill mode, informational in bulk
    if skill_name is not None and warnings:
        out.warn(warnings[0])
        raise typer.Exit(1)

    for warning in warnings:
        out.warn(warning)

    # report the outcome, phrased for one skill vs many
    display = (
        chosen_value.value
        if isinstance(chosen_value, LifecycleState)
        else str(chosen_value).lower()
    )

    if len(selected) == 1:
        out.success(f"Marked {selected[0].skill.name}: {chosen_key} = {display}.")
    else:
        names = ", ".join(r.skill.name for r in selected)
        out.success(f"{names} marked: {chosen_key}={display}.")


@app.callback()
def mark_skill(
    skill_name: Annotated[
        str | None,
        typer.Argument(help="Name of the skill to mark."),
    ] = None,
    *,
    bulk: Annotated[
        str | None,
        typer.Option(
            "--bulk", help="Comma-separated skill names to mark; skips the picker."
        ),
    ] = None,
    select_all: Annotated[
        bool, typer.Option("--all", help="Mark every skill in the Skill Library.")
    ] = False,
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
    # load skills from the Skill Library
    skills_root = skill_library()
    installed, errors = load_skills(skills_root)

    # resolve the Skill Selection from CLI flags
    try:
        selected = resolve_skill_selection(
            skill=skill_name, bulk=bulk, select_all=select_all, eligible=installed
        )
    except SkillSelectionError as exc:
        _report_selection_error(
            exc,
            skill_name=skill_name,
            bulk=bulk,
            select_all=select_all,
            errors=errors,
        )
        raise typer.Exit(1) from None

    # fall back to an interactive Skill Selection when no flag picked one
    selected = _resolve_selection(installed, selected)

    # resolve which marking to set (status or modified)
    if key is None:
        chosen_key = _prompt_for_key()
    else:
        _validate_key(key)
        chosen_key = key

    # resolve the value for that marking
    chosen_value = (
        _prompt_for_value(chosen_key)
        if value is None
        else _resolve_value(chosen_key, value)
    )

    _apply_and_report(
        selected,
        skill_name=skill_name,
        chosen_key=chosen_key,
        chosen_value=chosen_value,
    )
