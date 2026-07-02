"""Shared Skill Operation Pathway: selection, confirmation, and picker construction."""

from collections.abc import Callable, Sequence

import questionary

from mysk.io.skills import InstalledSkill


class SkillSelectionError(Exception):
    """Raised when `<skill>`/`--bulk`/`--all` are combined or name an unknown skill."""


def resolve_skill_selection(
    *,
    skill: str | None,
    bulk: str | None,
    select_all: bool,
    eligible: Sequence[InstalledSkill],
) -> list[InstalledSkill] | None:
    """Resolve a Skill Selection from `<skill>`/`--bulk`/`--all` against *eligible*.

    Returns None when none of the three are given, meaning the interactive
    picker should be shown instead. Raises SkillSelectionError if more than
    one of `skill`/`bulk`/`select_all` is given, or if `skill`/`bulk` names a
    skill not present in *eligible*.
    """
    given = sum([skill is not None, bulk is not None, select_all])
    if given > 1:
        msg = "<skill>, --bulk, and --all are mutually exclusive."
        raise SkillSelectionError(msg)

    if select_all:
        return list(eligible)

    if skill is not None:
        known = {r.skill.name for r in eligible}
        if skill not in known:
            msg = f"Unknown skill: {skill}"
            raise SkillSelectionError(msg)
        return [r for r in eligible if r.skill.name == skill]

    if bulk is None:
        return None

    known = {r.skill.name for r in eligible}
    names = {n.strip() for n in bulk.split(",")}
    unknown = names - known
    if unknown:
        msg = f"Unknown skill(s): {', '.join(sorted(unknown))}"
        raise SkillSelectionError(msg)
    return [r for r in eligible if r.skill.name in names]


def confirm(message: str, *, yes: bool) -> bool:
    """Return True immediately if *yes*, otherwise prompt the user with *message*."""
    if yes:
        return True
    return bool(questionary.confirm(message).ask())


def build_skill_choices(
    eligible: Sequence[InstalledSkill],
    *,
    relevance: Callable[[InstalledSkill], str | None],
) -> list[questionary.Choice]:
    """Build a `questionary.Choice` per skill in *eligible*, titled `name (state)`.

    *relevance* is called per skill; a None result leaves the choice
    selectable, a string result disables it and is shown as the reason.
    """
    return [
        questionary.Choice(
            f"{r.skill.name} ({r.mysk.state.value})",
            value=r,
            disabled=relevance(r),
        )
        for r in eligible
    ]
