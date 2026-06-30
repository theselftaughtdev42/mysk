"""LifecycleState enum: where a skill sits in its lifecycle."""

import enum


class LifecycleState(enum.Enum):
    """Where a skill sits in its lifecycle. Active is the implicit default."""

    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
