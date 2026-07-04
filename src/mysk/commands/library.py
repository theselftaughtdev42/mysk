"""Command to print the current Skill Library filepath."""

import typer

from mysk.console import console
from mysk.io.skills import skill_library_path

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


@app.callback()
def library_cmd() -> None:
    """Print the Skill Library filepath."""
    console.print(skill_library_path(), markup=False, soft_wrap=True)
