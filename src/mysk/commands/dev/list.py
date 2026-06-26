from rich import print as rprint
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from mysk.domain.lifecycle import LifecycleState
from mysk.io.skills import load_skills, skill_library

_STATUS_STYLE: dict[LifecycleState, str] = {
    LifecycleState.ACTIVE: "[green]active[/green]",
    LifecycleState.EXPERIMENTAL: "[yellow]experimental[/yellow]",
    LifecycleState.DEPRECATED: "[dim]deprecated[/dim]",
}


def dev_list() -> None:
    """Report lifecycle state, provenance, and schema compliance for every skill."""
    results = load_skills(skill_library())

    if not results:
        rprint("[dim]No skills in the Skill Library.[/dim]")
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

        if r.schema_error == "missing mysk block":
            schema_cell = "[red]missing mysk block[/red]"
        elif r.schema_error is not None:
            schema_cell = "[red]malformed[/red]"
        else:
            schema_cell = "[green]ok[/green]"

        table.add_row(escape(name), status_cell, provenance_cell, schema_cell)

    Console().print(table)
