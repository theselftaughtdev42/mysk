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
)

app = typer.Typer(
    name="mysk",
    help="Manage and deploy agent skills.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.command("list")(list.list_skills)
app.command("mark")(mark.mark_skill)
app.command("delete")(delete_skill.delete_skill)
app.command("deploy")(deploy.deploy)
app.command("import")(import_skill.import_skill)
app.command("refresh")(refresh_skill.refresh_skill)
app.command("cleanup")(cleanup.cleanup)
app.command("library")(library.library_cmd)
