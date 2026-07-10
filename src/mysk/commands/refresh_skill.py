"""Command to refresh an imported skill from its upstream source URL."""

import shutil
import tempfile
from pathlib import Path
from typing import Annotated, cast

import questionary
import typer

from mysk.domain.import_url import ImportUrl
from mysk.domain.skill import Skill
from mysk.io import frontmatter
from mysk.io.github import DownloadError, download_skill
from mysk.io.skills import InstalledSkill, load_skills, skill_library
from mysk.output import Output
from mysk.skill_operation_pathway import (
    SkillSelectionError,
    build_skill_choices,
    confirm,
    resolve_skill_selection,
)

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


def _refresh_relevance(result: InstalledSkill) -> str | None:
    if not result.mysk.provenance.has_upstream:
        return "no upstream — nothing to refresh"
    if result.mysk.provenance.modified:
        return "modified — needs review before refresh"
    return None


@app.callback()
def refresh_skill(
    name: Annotated[
        str | None, typer.Argument(help="Name of the skill to refresh.")
    ] = None,
    *,
    bulk: Annotated[
        str | None,
        typer.Option(
            "--bulk", help="Comma-separated skill names to refresh; skips the picker."
        ),
    ] = None,
    all_skills: Annotated[
        bool, typer.Option("--all", help="Refresh all imported skills.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", help="Skip confirmation prompt.")
    ] = False,
) -> None:
    """Refresh an imported skill from its upstream source URL."""
    # gather imported skills from the Skill Library
    library = skill_library()
    installed, _ = load_skills(library)
    imported = [r for r in installed if r.mysk.provenance.has_upstream]

    # resolve the Skill Selection from CLI flags
    try:
        selected = resolve_skill_selection(
            skill=name, bulk=bulk, select_all=all_skills, eligible=imported
        )
    except SkillSelectionError as exc:
        if name is None or bulk is not None or all_skills:
            out.error(str(exc))
            raise typer.Exit(1) from None
        selected = None

    # single named skill: refresh it directly, surfacing any error
    if name is not None:
        _refresh_one(name, library, yes=yes)
        return

    # fall back to an interactive Skill Selection when no flag picked one
    if selected is None:
        choices = build_skill_choices(installed, relevance=_refresh_relevance)
        selected = questionary.checkbox(
            "Select skills to refresh:\n", choices=choices
        ).ask()
        if not selected:
            out.note("Nothing selected.")
            raise typer.Exit(0)

    # partition the selection into refreshable and modified-needs-review
    refreshable = [r for r in selected if not r.mysk.provenance.modified]
    needs_review = [r for r in selected if r.mysk.provenance.modified]

    if not refreshable and not needs_review:
        out.note("No imported skills found in the Skill Library.")
        return

    # refresh each unmodified skill
    for result in refreshable:
        _refresh_one(result.dir.name, library, yes=yes)

    # list the modified skills skipped as needing review
    if needs_review:
        out.product(
            "\n[bold yellow]Needs review[/bold yellow] (modified: true — skipped):"
        )
        for result in needs_review:
            out.product(f"  {result.dir.name}", raw=True)


def _refresh_one(name: str, library: Path, *, yes: bool) -> None:
    skill_md_path = library / name / "SKILL.md"

    if not skill_md_path.exists():
        out.error(f"Skill {name!r} not found in the Skill Library.")
        raise typer.Exit(1)

    # load the skill's current SKILL.md from the Skill Library
    data, _ = frontmatter.read(skill_md_path.read_text())
    try:
        skill = Skill.from_frontmatter(data)
    except (ValueError, KeyError) as exc:
        out.error(f"Malformed SKILL.md: {exc}")
        raise typer.Exit(1) from None

    # refuse to refresh skills with no upstream or with local modifications
    if skill.mysk is None or not skill.mysk.provenance.has_upstream:
        out.error(
            f"{name!r} has no upstream to refresh from. "
            "Only skills with a source URL can be refreshed."
        )
        raise typer.Exit(1)

    if skill.mysk.provenance.modified:
        out.error(
            f"{name!r} has local changes (modified: true). "
            "Reset modified to false before refreshing."
        )
        raise typer.Exit(1)

    # parse the upstream source URL recorded in provenance
    source = cast("str", skill.mysk.provenance.source)
    try:
        import_url = ImportUrl.parse(source)
    except ValueError as exc:
        out.error(f"Cannot parse source URL {source!r}: {exc}")
        raise typer.Exit(1) from None

    local_dir = library / name

    # download the upstream skill into a temp staging dir
    out.info(f"refreshing {name!r} from {source}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_skill_dir = Path(tmp) / name
        try:
            download_skill(import_url, tmp_skill_dir)
        except DownloadError as exc:
            out.error(str(exc))
            raise typer.Exit(1) from None

        upstream_skill_md = tmp_skill_dir / "SKILL.md"
        if not upstream_skill_md.exists():
            out.error("Downloaded skill has no SKILL.md.")
            raise typer.Exit(1)

        # parse the freshly downloaded upstream skill
        upstream_data, upstream_body = frontmatter.read(upstream_skill_md.read_text())
        try:
            upstream_skill = Skill.from_frontmatter(upstream_data)
        except (ValueError, KeyError) as exc:
            out.error(f"Malformed upstream SKILL.md: {exc}")
            raise typer.Exit(1) from None

        # keep the local mysk block, take content from upstream
        refreshed = Skill(
            name=name,
            description=upstream_skill.description,
            mysk=skill.mysk,
            extra_fields=upstream_skill.extra_fields,
        )
        new_skill_md = frontmatter.write(refreshed.to_frontmatter(), upstream_body)

        (tmp_skill_dir / "SKILL.md").write_text(new_skill_md)

        # skip when nothing changed, otherwise confirm and replace local content
        if _dirs_are_identical(local_dir, tmp_skill_dir):
            out.note(f"No changes — {name!r} is already up to date.")
            return

        if not confirm(
            f"Refresh {name!r}? This will overwrite its local content.", yes=yes
        ):
            out.note(f"Aborted refresh of {name!r}.")
            return

        shutil.rmtree(local_dir)
        shutil.copytree(tmp_skill_dir, local_dir)

    out.success(f"Refreshed {name!r}.")


def _dirs_are_identical(a: Path, b: Path) -> bool:
    a_files = {p.relative_to(a) for p in a.rglob("*") if p.is_file()}
    b_files = {p.relative_to(b) for p in b.rglob("*") if p.is_file()}
    if a_files != b_files:
        return False
    return all((a / rel).read_bytes() == (b / rel).read_bytes() for rel in a_files)
