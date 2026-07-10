"""Entry point for the mysk CLI application."""

from importlib.metadata import version
from typing import Annotated

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
from mysk.output import Output

out = Output(__name__)

app = typer.Typer(
    name="mysk",
    help="Manage and deploy agent skills.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _version_callback(*, value: bool) -> None:
    """Print `mysk {version}` and exit early when `--version` is passed.

    Runs eagerly, before `main` — so it short-circuits ahead of logging setup
    and any subcommand. The version comes from installed package metadata, the
    single source of truth backed by `pyproject.toml`.
    """
    if value:
        out.product(f"mysk {version('mysk')}", raw=True)
        raise typer.Exit


@app.callback()
def main(
    *,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the installed version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Initialise mysk's diagnostic logging channel once per invocation.

    Exposes the eager `--version` flag; otherwise reads `MYSK_LOG_LEVEL` (via
    `configure_logging`) at startup.
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
