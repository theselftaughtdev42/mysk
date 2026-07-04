"""Shared Rich consoles for command screen output.

See ADR-0004 for the stdout/stderr contract and the markup-escape discipline.
"""

from rich.console import Console

console = Console()
err_console = Console(stderr=True)
