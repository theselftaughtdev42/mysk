"""Skill domain model: identity fields plus an optional mysk ownership block."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

from mysk.domain.lifecycle import LifecycleState
from mysk.domain.mysk_block import MyskBlock
from mysk.domain.provenance import Provenance


class Skill(BaseModel):
    """A skill: generic identity, plus an optional mysk block when owned.

    `name`/`description` are generic frontmatter any agent reads. `mysk` is
    present only once the skill has been adopted (migrated) into mysk
    management; an un-migrated skill carries no block (`mysk is None`).
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    mysk: MyskBlock | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_frontmatter(cls, data: dict) -> Self:
        """Build a Skill from a parsed frontmatter dict (inverse of to_frontmatter).

        A skill with no `mysk` key is un-migrated and gets `mysk=None`. When the
        `mysk` block is present it must carry a `state` — otherwise it is
        malformed and a ValueError is raised. Adding the block is the migrate
        command's job, never this layer's.
        """
        block = None
        if "mysk" in data:
            raw = data["mysk"]
            if not isinstance(raw, dict) or "state" not in raw:
                msg = "mysk block exists but is missing required 'state' key"
                raise ValueError(msg)
            block = MyskBlock(
                state=LifecycleState(raw["state"]),
                provenance=Provenance(
                    source=raw.get("source"),
                    modified=raw.get("modified", False),
                    upstream_name=raw.get("upstream_name"),
                ),
            )
        _known = {"name", "description", "mysk"}
        extra = {k: v for k, v in data.items() if k not in _known}
        return cls(
            name=data["name"],
            description=data["description"],
            mysk=block,
            extra_fields=extra,
        )

    def to_frontmatter(self) -> dict:
        """Render to a frontmatter dict with generic fields and the `mysk` block.

        An un-migrated skill emits no `mysk` key.
        """
        result: dict = {"name": self.name, "description": self.description}
        result.update(self.extra_fields)
        if self.mysk is not None:
            block: dict = {"state": self.mysk.state.value}
            if self.mysk.provenance.is_imported:
                block["source"] = self.mysk.provenance.source
                block["modified"] = self.mysk.provenance.modified
                if self.mysk.provenance.upstream_name is not None:
                    block["upstream_name"] = self.mysk.provenance.upstream_name
            result["mysk"] = block
        return result
