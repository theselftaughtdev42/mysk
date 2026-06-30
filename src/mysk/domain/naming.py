"""Validation helpers for skill names."""

import re

_VALID_NAME = re.compile(r"^[a-z-]+$")
_MAX_LEN = 64


def validate_skill_name(name: str) -> None:
    """Raise ValueError if *name* is not a valid skill name."""
    if not _VALID_NAME.match(name):
        msg = f"Skill name {name!r} must contain only lowercase letters and hyphens."
        raise ValueError(msg)
    if len(name) > _MAX_LEN:
        msg = f"Skill name {name!r} exceeds the maximum of {_MAX_LEN} characters."
        raise ValueError(msg)
