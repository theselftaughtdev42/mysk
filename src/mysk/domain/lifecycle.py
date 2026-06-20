import enum


class LifecycleState(enum.Enum):
    """Where a skill sits in its lifecycle. Active is the implicit default."""

    INIT = "init"
    ACTIVE = "active"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"
