"""Command to import a skill from a GitHub URL or local directory."""

import shutil
import tempfile
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich.markup import escape
from rich.rule import Rule

from mysk.console import console, err_console
from mysk.domain.import_url import ImportUrl, RepoRootUrl
from mysk.domain.lifecycle import LifecycleState
from mysk.domain.mysk_block import MyskBlock
from mysk.domain.naming import validate_skill_name
from mysk.domain.provenance import Provenance
from mysk.domain.skill import Skill
from mysk.io import frontmatter
from mysk.io.github import DownloadError, download_skill, scan_repo_for_skills
from mysk.io.skills import CollisionError, check_collision, skill_library

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)

_LIFECYCLE_CHOICES = [
    LifecycleState.EXPERIMENTAL.value,
    LifecycleState.ACTIVE.value,
]


@app.callback()
def import_skill(
    url: Annotated[
        str, typer.Argument(help="GitHub URL or local path of the skill directory.")
    ],
    rename: Annotated[
        str | None,
        typer.Option("--rename", help="Import the skill under a different local name."),
    ] = None,
) -> None:
    """Import a skill from a GitHub URL or local path into the Skill Library."""
    local_path = Path(url).expanduser()
    if local_path.exists() and local_path.is_dir():
        if (local_path / "SKILL.md").exists():
            _import_from_local_path(local_path, rename)
        else:
            _import_from_local_dir(local_path)
        return

    try:
        import_url = ImportUrl.parse(url)
    except ValueError:
        _import_from_repo_root(url)
        return

    _import_single(import_url, url, rename)


def _import_from_local_dir(path: Path) -> None:
    skill_dirs = sorted(
        d for d in path.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    )

    if not skill_dirs:
        err_console.print("[red]Error:[/red] No skills found in this directory.")
        raise typer.Exit(1)

    selected_names = questionary.checkbox(
        "Choose skills to import:", choices=[d.name for d in skill_dirs]
    ).ask()
    if not selected_names:
        raise typer.Exit(1)

    skill_dir_map = {d.name: d for d in skill_dirs}
    library = skill_library()
    total = len(selected_names)
    imported = 0

    for i, name in enumerate(selected_names, 1):
        skill_dir = skill_dir_map[name]

        console.print()
        console.print(
            Rule(
                f"[bold]{escape(name)}[/bold]  [dim]{i} of {total}[/dim]",
                align="left",
            )
        )

        local_name = _resolve_local_name(
            library,
            name,
            None,
            prompt=f"Enter a new local name for {name!r}, or leave blank to skip:",
        )
        if local_name is None:
            continue

        data, body = frontmatter.read((skill_dir / "SKILL.md").read_text())
        try:
            local_skill = Skill.from_frontmatter(data)
        except (ValueError, KeyError) as exc:
            err_console.print(
                f"[red]Error:[/red] Malformed SKILL.md: {escape(str(exc))}"
            )
            continue

        if local_name == name and local_skill.name != name:
            err_console.print(
                f"[red]Error:[/red] The skill's name field "
                f"{escape(repr(local_skill.name))} does not match the directory "
                f"name {escape(repr(name))}. Fix the SKILL.md and re-import."
            )
            continue

        state_value = questionary.select(
            "Choose a lifecycle state:", choices=_LIFECYCLE_CHOICES
        ).ask()
        if state_value is None:
            raise typer.Exit(1)

        mysk_block = MyskBlock(
            state=LifecycleState(state_value),
            provenance=Provenance(),
        )
        final_skill = Skill(
            name=local_name,
            description=local_skill.description,
            mysk=mysk_block,
            extra_fields=local_skill.extra_fields,
        )
        dest = library / local_name
        _write_skill_to_library(
            skill_dir, frontmatter.write(final_skill.to_frontmatter(), body), dest
        )
        imported += 1

    console.print()
    console.print(Rule(style="dim"))
    console.print(
        f"Imported [bold]{imported}[/bold] of [bold]{total}[/bold] selected skills."
    )


def _import_from_repo_root(url: str) -> None:
    try:
        repo_root_url = RepoRootUrl.parse(url)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from None

    try:
        skill_paths = scan_repo_for_skills(repo_root_url)
    except DownloadError as exc:
        err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from None

    if not skill_paths:
        err_console.print("[red]Error:[/red] No skills found in this repository.")
        raise typer.Exit(1)

    selected_paths = questionary.checkbox(
        "Choose skills to import:", choices=skill_paths
    ).ask()
    if not selected_paths:
        raise typer.Exit(1)

    library = skill_library()
    total = len(selected_paths)
    imported = 0

    for i, path in enumerate(selected_paths, 1):
        skill_url = repo_root_url.skill_url(path)
        import_url = ImportUrl.parse(skill_url)
        upstream_dir_name = import_url.skill_dir_name

        console.print()
        console.print(
            Rule(
                f"[bold]{escape(upstream_dir_name)}[/bold]  [dim]{i} of {total}[/dim]",
                align="left",
            )
        )

        local_name = _resolve_local_name(
            library,
            upstream_dir_name,
            skill_url,
            prompt=(
                f"Enter a new local name for {upstream_dir_name!r}, "
                "or leave blank to skip:"
            ),
        )
        if local_name is None:
            continue

        rename = local_name if local_name != upstream_dir_name else None
        _import_single(import_url, skill_url, rename)
        imported += 1

    console.print()
    console.print(Rule(style="dim"))
    console.print(
        f"Imported [bold]{imported}[/bold] of [bold]{total}[/bold] selected skills."
    )


def _resolve_local_name(
    library: Path,
    preferred: str,
    source: str | None,
    *,
    prompt: str,
) -> str | None:
    try:
        check_collision(library, preferred, source)
    except CollisionError as exc:
        err_console.print(f"[red]Collision:[/red] {escape(str(exc))}")
        new_name = questionary.text(prompt).ask()
        if not new_name:
            return None
        try:
            validate_skill_name(new_name)
        except ValueError as ve:
            err_console.print(f"[red]Error:[/red] {escape(str(ve))}")
            return None
        try:
            check_collision(library, new_name, source)
        except CollisionError as ce:
            err_console.print(f"[red]Error:[/red] {escape(str(ce))}")
            return None
        return new_name
    return preferred


def _write_skill_to_library(src: Path, skill_md_content: str, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / dest.name
        shutil.copytree(src, staging)
        (staging / "SKILL.md").write_text(skill_md_content)
        shutil.copytree(staging, dest)


def _import_from_local_path(path: Path, rename: str | None = None) -> None:
    local_name = rename if rename is not None else path.name

    try:
        validate_skill_name(local_name)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from None

    library = skill_library()

    resolved_name = _resolve_local_name(
        library,
        local_name,
        None,
        prompt="Enter a new local name, or leave blank to cancel:",
    )
    if resolved_name is None:
        raise typer.Exit(1)
    local_name = resolved_name

    skill_md_path = path / "SKILL.md"
    if not skill_md_path.exists():
        err_console.print("[red]Error:[/red] Skill directory has no SKILL.md.")
        raise typer.Exit(1)

    data, body = frontmatter.read(skill_md_path.read_text())
    try:
        local_skill = Skill.from_frontmatter(data)
    except (ValueError, KeyError) as exc:
        err_console.print(f"[red]Error:[/red] Malformed SKILL.md: {escape(str(exc))}")
        raise typer.Exit(1) from None

    if rename is None and local_skill.name != path.name:
        err_console.print(
            f"[red]Error:[/red] The skill's name field "
            f"{escape(repr(local_skill.name))} does not match the directory name "
            f"{escape(repr(path.name))}. "
            f"Skills must satisfy the Agent Skills naming constraint."
        )
        raise typer.Exit(1)

    state_value = questionary.select(
        "Choose a lifecycle state:",
        choices=_LIFECYCLE_CHOICES,
    ).ask()
    if state_value is None:
        raise typer.Exit(1)

    mysk_block = MyskBlock(
        state=LifecycleState(state_value),
        provenance=Provenance(),
    )
    final_skill = Skill(
        name=local_name,
        description=local_skill.description,
        mysk=mysk_block,
        extra_fields=local_skill.extra_fields,
    )

    dest = library / local_name
    _write_skill_to_library(
        path, frontmatter.write(final_skill.to_frontmatter(), body), dest
    )


def _import_single(import_url: ImportUrl, url: str, rename: str | None) -> None:
    upstream_dir_name = import_url.skill_dir_name
    local_name = rename if rename is not None else upstream_dir_name

    try:
        validate_skill_name(local_name)
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from None

    library = skill_library()

    resolved_name = _resolve_local_name(
        library,
        local_name,
        url,
        prompt="Enter a new local name, or leave blank to cancel:",
    )
    if resolved_name is None:
        raise typer.Exit(1)
    if resolved_name != local_name:
        rename = resolved_name
    local_name = resolved_name

    with tempfile.TemporaryDirectory() as tmp:
        tmp_skill_dir = Path(tmp) / local_name
        try:
            download_skill(import_url, tmp_skill_dir)
        except DownloadError as exc:
            err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
            raise typer.Exit(1) from None

        skill_md_path = tmp_skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            err_console.print("[red]Error:[/red] Downloaded skill has no SKILL.md.")
            raise typer.Exit(1)

        data, body = frontmatter.read(skill_md_path.read_text())
        try:
            downloaded_skill = Skill.from_frontmatter(data)
        except (ValueError, KeyError) as exc:
            err_console.print(
                f"[red]Error:[/red] Malformed SKILL.md in downloaded skill: "
                f"{escape(str(exc))}"
            )
            raise typer.Exit(1) from None

        if downloaded_skill.name != upstream_dir_name:
            err_console.print(
                f"[red]Error:[/red] The skill's name field "
                f"{escape(repr(downloaded_skill.name))} does not match the upstream "
                f"directory name {escape(repr(upstream_dir_name))}. "
                f"Skills must satisfy the Agent Skills naming constraint."
            )
            raise typer.Exit(1)

        state_value = questionary.select(
            "Choose a lifecycle state:",
            choices=_LIFECYCLE_CHOICES,
        ).ask()
        if state_value is None:
            raise typer.Exit(1)

        upstream_name = upstream_dir_name if rename is not None else None
        provenance = Provenance(source=url, modified=False, upstream_name=upstream_name)
        mysk_block = MyskBlock(
            state=LifecycleState(state_value),
            provenance=provenance,
        )
        final_skill = Skill(
            name=local_name,
            description=downloaded_skill.description,
            mysk=mysk_block,
            extra_fields=downloaded_skill.extra_fields,
        )
        dest = library / local_name
        _write_skill_to_library(
            tmp_skill_dir, frontmatter.write(final_skill.to_frontmatter(), body), dest
        )
