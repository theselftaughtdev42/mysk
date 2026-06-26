import typer

from mysk.commands import (
    cleanup,
    delete_skill,
    deploy,
    import_skill,
    library,
    list,
    mark,
    refresh_skill,
    undeploy,
)

app = typer.Typer(
    name="mysk",
    help="Manage and deploy agent skills.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(import_skill.app, name="import")
app.add_typer(deploy.app, name="deploy")

app.add_typer(cleanup.app, name="cleanup")
app.add_typer(delete_skill.app, name="delete")
app.add_typer(library.app, name="library")
app.add_typer(list.app, name="list")
app.add_typer(mark.app, name="mark")
app.add_typer(refresh_skill.app, name="refresh")
app.add_typer(undeploy.app, name="undeploy")
