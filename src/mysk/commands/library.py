"""Command to print the current Skill Library filepath."""

import typer

from mysk.io.skills import skill_library_path

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


@app.callback()
def library_cmd() -> None:
    """Print the Skill Library filepath."""
    typer.echo(skill_library_path())
