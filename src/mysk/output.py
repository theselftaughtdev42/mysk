"""The Output facade — mysk's unified presentation and diagnostics surface.

Instantiated per module as `out = Output(__name__)`. The facade owns two
channels kept strictly separate by *audience*, not severity:

- **Presentation** (`product`/`success`/`note`/`warn`/`error`) →
  the shared Rich consoles, always shown, routed to stdout/stderr per ADR-0004.
- **Diagnostics** (`debug`/`info`/`exception`) → stdlib `logging`,
  hidden unless `MYSK_LOG_LEVEL` is set.

See the two-channel ADR for the full rationale and the ADR-0004 carve-out.
"""

import logging

from rich.console import RenderableType
from rich.markup import escape

from mysk.console import console, err_console


class Output:
    """Per-module facade over mysk's presentation and diagnostic channels."""

    def __init__(self, name: str) -> None:
        """Bind the facade to *name* (pass `__name__` from the calling module)."""
        self._logger = logging.getLogger(name)

    def product(self, message: RenderableType, *, raw: bool = False) -> None:
        """Emit the command's product to stdout.

        Accepts any Rich renderable (a string, or a table/rule/etc). Pass
        `raw=True` for pure-data string lines (paths, per-target reports): markup
        parsing is bypassed and the line is soft-wrapped so long values emit
        verbatim. The default styled mode is the escape hatch for intentionally
        Rich-formatted product (section rules, progress, tables).
        """
        if raw:
            console.print(message, markup=False, soft_wrap=True)
        else:
            console.print(message)

    def success(self, message: str) -> None:
        """Emit a success confirmation to stdout."""
        console.print(f"[green]{escape(message)}[/green]")

    def note(self, message: str) -> None:
        """Emit a neutral "nothing to do" notice to stdout."""
        console.print(escape(message))

    def warn(self, message: str) -> None:
        """Emit a warning to stderr, prefixed with a styled `Warning:` label."""
        err_console.print(f"[yellow]Warning:[/yellow] {escape(message)}")

    def error(self, message: str) -> None:
        """Emit an error to stderr, prefixed with a styled `Error:` label."""
        err_console.print(f"[red]Error:[/red] {escape(message)}")

    def debug(self, message: str) -> None:
        """Emit a DEBUG diagnostic breadcrumb (hidden unless opted in)."""
        self._logger.debug(message, stacklevel=2)

    def info(self, message: str) -> None:
        """Emit an INFO diagnostic milestone (hidden unless opted in)."""
        self._logger.info(message, stacklevel=2)

    def exception(self, message: str) -> None:
        """Emit an ERROR diagnostic with the active exception's traceback.

        Call from within an `except` block to capture a swallowed exception's
        full traceback on the diagnostic channel while the user sees only a
        clean one-line presentation error.
        """
        self._logger.exception(message, stacklevel=2)
