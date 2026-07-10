"""Provenance model: tracks whether a skill has an upstream or is standalone."""

from pydantic import BaseModel, ConfigDict


class Provenance(BaseModel):
    """Whether a skill has an upstream `source` or is standalone.

    A `source` URL means the skill has an upstream it can be refreshed from;
    `modified` tracks whether the local copy has drifted from that upstream.
    Standalone skills carry neither.
    """

    model_config = ConfigDict(frozen=True)

    source: str | None = None
    modified: bool = False
    upstream_name: str | None = None

    @property
    def has_upstream(self) -> bool:
        """Return True when this skill has an upstream `source` URL to refresh from."""
        return self.source is not None
