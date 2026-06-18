import sys

import typer
from rich import print as rprint
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from mysk.domain.lifecycle import LifecycleState
from mysk.io.skills import load_skills
from mysk.io.source_repo import find_source_repo

_STATUS_STYLE: dict[LifecycleState, str] = {
    LifecycleState.ACTIVE: "[green]active[/green]",
    LifecycleState.EXPERIMENTAL: "[yellow]experimental[/yellow]",
    LifecycleState.DEPRECATED: "[dim]deprecated[/dim]",
    LifecycleState.INIT: "[dim italic]init[/dim italic]",
}


def dev_list() -> None:
    """Report lifecycle state, provenance, and schema compliance for every skill."""
    repo = find_source_repo()
    if repo is None:
        rprint(
            "[red]mysk dev list must be run from inside the mysk source repo.[/red]",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    results = load_skills(repo / "skills")

    if not results:
        rprint("[dim]No skills found in skills/.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Provenance")
    table.add_column("Schema")

    for r in results:
        name = r.path.parent.name

        if r.skill is not None and r.skill.mysk is not None:
            status_cell = _STATUS_STYLE[r.skill.mysk.state]
            prov = r.skill.mysk.provenance
            if prov.is_imported:
                provenance_cell = (
                    "[yellow]imported ⚠ modified[/yellow]"
                    if prov.modified
                    else "imported"
                )
            else:
                provenance_cell = "self-authored"
        else:
            status_cell = "[dim]—[/dim]"
            provenance_cell = "[dim]—[/dim]"

        if r.schema_error is not None:
            schema_cell = "[red]malformed[/red]"
        elif r.is_unmigrated:
            schema_cell = "[yellow]needs migrate[/yellow]"
        else:
            schema_cell = "[green]ok[/green]"

        table.add_row(escape(name), status_cell, provenance_cell, schema_cell)

    Console().print(table)
