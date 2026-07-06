"""Command to list all skills and their deployment status."""

import typer
from rich.markup import escape
from rich.table import Table

from mysk.domain.lifecycle import LifecycleState
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets, is_deployed
from mysk.output import Output

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)

_HIGHLIGHTED = {LifecycleState.ACTIVE, LifecycleState.EXPERIMENTAL}


@app.callback()
def list_skills() -> None:
    """List all skills and where they are deployed."""
    # load skills from the Skill Library and discover Deployment Targets
    library = skill_library()
    installed, errors = load_skills(library)
    targets = discover_targets()

    table = Table(show_header=True, header_style="bold", show_lines=True)
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Provenance")
    table.add_column("Deployed To")

    # render each installed skill with its status, provenance, and where deployed
    for r in installed:
        state = r.mysk.state
        prov = r.mysk.provenance
        provenance_label = (
            ("imported ⚠ modified" if prov.modified else "imported")
            if prov.is_imported
            else "self-authored"
        )
        deployed_to = [t for t in targets if is_deployed(t, r.skill, library)]
        deployed_label = escape("\n".join(t.label() for t in deployed_to) or "—")
        name = escape(r.skill.name)
        if state in _HIGHLIGHTED and deployed_to:
            table.add_row(
                f"[bold]{name}[/bold]",
                state.value,
                provenance_label,
                deployed_label,
            )
        else:
            table.add_row(
                f"[dim]{name}[/dim]",
                f"[dim]{state.value}[/dim]",
                f"[dim]{provenance_label}[/dim]",
                f"[dim]{deployed_label}[/dim]",
                style="dim",
            )

    # render skills that failed to load as dimmed rows
    for r in errors:
        name = escape(r.path.parent.name)
        status_label = (
            "no mysk block" if r.schema_error == "missing mysk block" else "malformed"
        )
        table.add_row(
            f"[dim]{name}[/dim]",
            f"[dim]{status_label}[/dim]",
            "[dim]—[/dim]",
            "[dim]—[/dim]",
            style="dim",
        )

    out.product(table)

    if not targets:
        out.product(
            "\n[yellow]No deployment targets found."
            "Run [bold]mysk deploy[/bold] to deploy your skills.[/yellow]"
        )
