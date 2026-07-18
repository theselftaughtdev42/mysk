"""Shared Skill Operation Pathway: selection, confirmation, and reporting."""

from collections.abc import Callable, Sequence

import questionary

from mysk.io.deploy import ActResult
from mysk.io.skills import InstalledSkill
from mysk.io.targets import Target
from mysk.output import Output

out = Output(__name__)


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


def report_act(
    targets: Sequence[Target],
    skills: Sequence[InstalledSkill],
    *,
    act: Callable[[InstalledSkill, Target], ActResult],
    prepare_target: Callable[[Target], None] = lambda _: None,
) -> None:
    """Run *act* over every skill at every target, reporting each outcome.

    The final stage of the Skill Operation Pathway, shared by `deploy`,
    `undeploy`, and `cleanup`. For each target in *targets*, print the
    blank-line-separated `name:` roster header, call *prepare_target* (a no-op by
    default; `deploy` uses it to create and announce a missing target directory),
    then run *act* on each skill and print its outcome line, suffixing the
    reason in parentheses when one is present.
    """
    for target in targets:
        out.product(f"\n{target.name}:", raw=True)
        prepare_target(target)
        for skill in skills:
            result = act(skill, target)
            line = f"  {skill.skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            out.product(line, raw=True)
