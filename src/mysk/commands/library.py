"""Command to print the current Skill Library filepath."""

import typer

from mysk.io.skills import skill_library_path
from mysk.output import Output

out = Output(__name__)

app = typer.Typer(
    invoke_without_command=True, context_settings={"allow_interspersed_args": True}
)


@app.callback()
def library_cmd() -> None:
    """Print the Skill Library filepath."""
    out.product(str(skill_library_path()), raw=True)
