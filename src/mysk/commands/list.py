"""Command to list all skills and their deployment status."""

from typing import Annotated

import typer
from rich.console import RenderableType
from rich.markup import escape
from rich.style import Style
from rich.table import Table
from rich.text import Text

from mysk.domain.lifecycle import LifecycleState
from mysk.io.skills import load_skills, skill_library
from mysk.io.targets import discover_targets, is_deployed
from mysk.output import Output

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)

_HIGHLIGHTED = {LifecycleState.ACTIVE, LifecycleState.EXPERIMENTAL}


def _upstream_url_cell(source: str | None) -> RenderableType:
    """Render the Upstream URL cell: a clickable link to *source*, or — if standalone.

    The URL is wrapped in an OSC 8 hyperlink so terminals can open it on click
    even though the cell folds the visible text across lines.
    """
    if source is None:
        return "—"
    return Text(source, style=Style(link=source))


@app.callback()
def list_skills(
    *,
    upstream_urls: Annotated[
        bool,
        typer.Option(
            "--upstream-urls",
            help="Show each skill's upstream source URL instead of a yes/no column.",
        ),
    ] = False,
) -> None:
    """List all skills and where they are deployed."""
    # load skills from the Skill Library and discover Deployment Targets
    library = skill_library()
    installed, errors = load_skills(library)
    targets = discover_targets()

    table = Table(show_header=True, header_style="bold", show_lines=True)
    table.add_column("Name")
    table.add_column("Status")
    # the upstream column is either a yes/no fact or the full source URL; the URL
    # is folded (wrapped) rather than truncated so it is always shown in full
    if upstream_urls:
        table.add_column("Upstream URL", overflow="fold")
    else:
        table.add_column("Has Upstream")
    table.add_column("Modified")
    table.add_column("Deployed To")

    # render each installed skill with its upstream/modified facts and where deployed
    for r in installed:
        state = r.mysk.state
        prov = r.mysk.provenance
        if upstream_urls:
            upstream_cell: RenderableType = _upstream_url_cell(prov.source)
        else:
            upstream_cell = "yes" if prov.has_upstream else "no"
        # modified is meaningful only with an upstream; standalone skills read "—"
        if prov.has_upstream:
            modified_label = "yes" if prov.modified else "no"
        else:
            modified_label = "—"
        deployed_to = [t for t in targets if is_deployed(t, r.skill, library)]
        deployed_label = escape("\n".join(t.label() for t in deployed_to) or "—")
        name = escape(r.skill.name)
        if state in _HIGHLIGHTED and deployed_to:
            table.add_row(
                f"[bold]{name}[/bold]",
                state.value,
                upstream_cell,
                modified_label,
                deployed_label,
            )
        else:
            # the whole row is dimmed via style="dim"; the upstream cell is passed
            # as-is so a hyperlink Text keeps its link (dim layers over it)
            table.add_row(
                f"[dim]{name}[/dim]",
                f"[dim]{state.value}[/dim]",
                upstream_cell,
                f"[dim]{modified_label}[/dim]",
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
            "[dim]—[/dim]",
            style="dim",
        )

    out.product(table)

    if not targets:
        out.product(
            "\n[yellow]No deployment targets found."
            "Run [bold]mysk deploy[/bold] to deploy your skills.[/yellow]"
        )
