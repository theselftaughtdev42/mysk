import sys

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from mysk.io.skills import load_skills
from mysk.io.source_repo import find_source_repo
from mysk.io.targets import discover_targets, is_deployed


def list_skills() -> None:
    """List all skills and where they are deployed."""
    repo = find_source_repo()
    if repo is None:
        rprint("[red]Cannot find the mysk source repo.[/red]", file=sys.stderr)
        raise typer.Exit(1)

    skills = load_skills(repo / "skills")
    targets = discover_targets()

    console = Console()
    table = Table(show_header=True, header_style="bold", show_lines=True)
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Deployed To")

    for skill in skills:
        state = skill.mysk.state
        deployed_to = [t for t in targets if is_deployed(t, skill)]
        deployed_label = "\n".join(t.label() for t in deployed_to) or "—"
        if state.is_deployable and deployed_to:
            table.add_row(f"[bold]{skill.name}[/bold]", state.value, deployed_label)
        else:
            table.add_row(
                f"[dim]{skill.name}[/dim]",
                f"[dim]{state.value}[/dim]",
                f"[dim]{deployed_label}[/dim]",
                style="dim",
            )

    console.print(table)

    if not targets:
        rprint(
            "\n[yellow]No deployment targets found."
            "Run [bold]mysk deploy[/bold] to deploy your skills.[/yellow]"
        )
