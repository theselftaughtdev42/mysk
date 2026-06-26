from typing import cast

import typer

from mysk.domain.lifecycle import LifecycleState
from mysk.domain.skill import Skill
from mysk.io.deploy import remove_skill
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets


def confirm(msg: str) -> bool:
    return typer.confirm(msg)


def cleanup() -> None:
    """Remove deprecated skills from all Deployment Targets."""
    library = skill_library()
    all_skills = load_skills(library)
    deprecated = [
        r
        for r in all_skills
        if r.skill is not None
        and r.skill.mysk is not None
        and r.skill.mysk.state == LifecycleState.DEPRECATED
    ]

    if not deprecated:
        print("Nothing to clean up.")
        raise typer.Exit(0)

    targets = discover_targets()

    skill_names = ", ".join(r.skill.name for r in deprecated if r.skill)
    target_names = ", ".join(t.name for t in targets)
    if not confirm(
        f"Remove {len(deprecated)} deprecated skill(s) ({skill_names}) "
        f"from {len(targets)} target(s) ({target_names})?"
    ):
        raise typer.Exit(0)

    for target in targets:
        print(f"\n{target.name}:")
        for skill_result in deprecated:
            skill = cast(Skill, skill_result.skill)
            target_path = target.path / skill.name
            result = remove_skill(target_path, skill_library_path=library)
            line = f"  {skill.name}: {result.outcome}"
            if result.reason:
                line += f" ({result.reason})"
            print(line)
