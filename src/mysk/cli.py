"""Entry point for the mysk CLI application."""

import typer

from mysk.commands import (
    cleanup,
    delete_skill,
    deploy,
    import_skill,
    library,
    mark,
    refresh_skill,
    undeploy,
)
from mysk.commands import (
    list as list_skills,
)
from mysk.logging_config import configure_logging

app = typer.Typer(
    name="mysk",
    help="Manage and deploy agent skills.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.callback()
def main() -> None:
    """Initialise mysk's diagnostic logging channel once per invocation.

    Takes no parameters, so it introduces no CLI flag; it only reads
    `MYSK_LOG_LEVEL` (via `configure_logging`) at startup.
    """
    configure_logging()


app.add_typer(import_skill.app, name="import")
app.add_typer(deploy.app, name="deploy")

app.add_typer(cleanup.app, name="cleanup")
app.add_typer(delete_skill.app, name="delete")
app.add_typer(library.app, name="library")
app.add_typer(list_skills.app, name="list")
app.add_typer(mark.app, name="mark")
app.add_typer(refresh_skill.app, name="refresh")
app.add_typer(undeploy.app, name="undeploy")
