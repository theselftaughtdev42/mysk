import typer

from mysk.commands import deploy, init
from mysk.commands import list as list_cmd
from mysk.commands.dev import list as dev_list
from mysk.commands.dev import mark as dev_mark
from mysk.commands.dev import migrate as dev_migrate

app = typer.Typer(
    name="mysk",
    help="Manage and deploy agent skills.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

dev_app = typer.Typer(
    help="Developer utilities for skill lifecycle management.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(dev_app, name="dev")

app.command("list")(list_cmd.list_skills)
app.command("deploy")(deploy.deploy)
app.command("init")(init.init)

dev_app.command("list")(dev_list.dev_list)
dev_app.command("mark")(dev_mark.dev_mark)
dev_app.command("migrate")(dev_migrate.dev_migrate)
