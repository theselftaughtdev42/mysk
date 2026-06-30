"""Provenance model: tracks whether a skill is self-authored or imported."""

from pydantic import BaseModel, ConfigDict


class Provenance(BaseModel):
    """Whether a skill is self-authored or imported from an external source.

    A `source` URL marks the skill as imported; `modified` tracks whether the
    local copy has drifted from upstream. Self-authored skills carry neither.
    """

    model_config = ConfigDict(frozen=True)

    source: str | None = None
    modified: bool = False
    upstream_name: str | None = None

    @property
    def is_imported(self) -> bool:
        """Return True when this skill was imported from an external source URL."""
        return self.source is not None
