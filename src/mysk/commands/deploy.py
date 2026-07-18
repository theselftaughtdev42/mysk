"""Command to deploy skills to selected Deployment Targets."""

from collections.abc import Sequence
from pathlib import Path

import questionary
import typer

from mysk.io.deploy import ActResult, reconcile_skill
from mysk.io.skills import InstalledSkill, load_skills, skill_library
from mysk.io.targets import (
    Target,
    UnknownAgentsError,
    discover_targets,
    narrow_targets,
)
from mysk.output import Output
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    confirm,
    report_act,
    resolve_skill_selection,
)

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def _already_deployed(result: InstalledSkill, targets: Sequence[Target]) -> str | None:
    for target in targets:
        target_path = target.path / result.skill.name
        cleanly_deployed = (
            target_path.is_symlink() and target_path.resolve() == result.dir.resolve()
        )
        if not cleanly_deployed:
            return None
    return "already deployed"


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
    skill: str | None = typer.Argument(None, help="Name of a single skill to deploy."),
    *,
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Replace non-symlink directories at collision paths."
    ),
    agents: str | None = typer.Option(
        None,
        "--agents",
        help="Comma-separated agent names; defaults to all found.",
    ),
    bulk: str | None = typer.Option(
        None,
        "--bulk",
        help="Comma-separated skill names to deploy; skips the skill prompt.",
    ),
    select_all: bool = typer.Option(
        False,
        "--all",
        help="Deploy every skill without prompting; skips the skill prompt.",
    ),
    yes: bool = typer.Option(
        False, "--yes", help="Skip confirmation before replacing a real directory."
    ),
) -> None:
    """Deploy skills to selected Deployment Targets."""
    # discover the available Deployment Targets
    targets = discover_targets()

    # resolve the Deployment Targets: all found by default, narrowed with --agents
    if not targets:
        out.note(
            "No Deployment Targets found. "
            "Install an agent (claude, cursor, codex) first."
        )
        raise typer.Exit(0)
    try:
        selected_targets = narrow_targets(targets, agents)
    except UnknownAgentsError as exc:
        out.error(str(exc))
        raise typer.Exit(1) from None

    # load deployable skills from the Skill Library
    library = skill_library()
    deployable, _ = load_skills(library)

    if not deployable:
        out.note("No skills in the Skill Library to deploy.")
        raise typer.Exit(0)

    # announce the resolved target roster before any filesystem changes
    out.product(
        f"Deploying to {len(selected_targets)} targets: "
        f"{', '.join(t.name for t in selected_targets)}",
        raw=True,
    )

    # resolve the Skill Selection from CLI flags
    try:
        selected_skills = resolve_skill_selection(
            skill=skill, bulk=bulk, select_all=select_all, eligible=deployable
        )
    except SkillSelectionError as exc:
        out.error(str(exc))
        raise typer.Exit(1) from None

    # fall back to an interactive Skill Selection when no flag picked one
    if selected_skills is None:
        skill_choices = build_skill_choices(
            deployable,
            relevance=lambda r: _already_deployed(r, selected_targets),
        )
        if all(choice.disabled for choice in skill_choices):
            out.note("All skills already deployed to selected target(s).")
            raise typer.Exit(0)
        selected_skills = questionary.checkbox(
            "Select skills to deploy:\n",
            choices=skill_choices,
        ).ask()

    if not selected_skills:
        out.note("Nothing selected.")
        raise typer.Exit(0)

    # deploy each selected skill to each target
    out.info(
        f"deploying {len(selected_skills)} skill(s) to "
        f"{len(selected_targets)} target(s)"
    )

    def _announce_new_dir(target: Target) -> None:
        created = _ensure_target_dir(target.path)
        if created:
            out.product(f"  Created {created}", raw=True)

    def _deploy_one(skill_result: InstalledSkill, target: Target) -> ActResult:
        target_path = target.path / skill_result.skill.name
        destroys_real_dir = (
            overwrite and target_path.exists() and not target_path.is_symlink()
        )
        if destroys_real_dir:
            message = (
                f"'{target_path}' is a real directory, not a mysk symlink. Replace it?"
            )
            if not confirm(message, yes=yes):
                return ActResult(outcome="skipped", reason="declined")
        return reconcile_skill(
            skill_result.dir,
            target_path,
            overwrite=overwrite,
            skill_library_path=library,
        )

    report_act(
        selected_targets,
        selected_skills,
        act=_deploy_one,
        prepare_target=_announce_new_dir,
    )
