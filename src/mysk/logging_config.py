"""Central configuration for mysk's diagnostic logging channel.

`configure_logging()` is called once from the root Typer callback on every
invocation. It reads `MYSK_LOG_LEVEL` exactly once and makes "off by default"
a *structural* guarantee: when the variable is unset the `mysk` logger gets a
`NullHandler` (so Python's last-resort handler can never leak a WARNING+ or
traceback to stderr uninvited), and the emitting `RichHandler` is attached
only when the variable is set.

See the two-channel ADR for the full rationale.
"""

import logging
import os

from rich.logging import RichHandler

from mysk.console import err_console

MYSK_LOGGER = "mysk"


def configure_logging() -> None:
    """Configure the `mysk` diagnostic logger from `MYSK_LOG_LEVEL`.

    Idempotent: safe to call on every invocation without accumulating handlers.
    """
    logger = logging.getLogger(MYSK_LOGGER)
    logger.handlers.clear()

    level_name = os.environ.get("MYSK_LOG_LEVEL")
    if level_name is None:
        logger.addHandler(logging.NullHandler())
        return

    level = logging.getLevelNamesMapping()[level_name]
    logger.setLevel(level)
    logger.addHandler(
        RichHandler(
            console=err_console,
            show_level=True,
            show_path=True,
            show_time=False,
            markup=False,
            rich_tracebacks=True,
        )
    )

    # Cascade: DEBUG turns on httpx request/response lines (INFO), so HTTP
    # visibility is one knob away. Full wire detail stays available by raising
    # the httpx logger to DEBUG manually.
    if level <= logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.INFO)
