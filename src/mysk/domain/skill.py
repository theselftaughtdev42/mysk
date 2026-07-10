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
    def from_frontmatter(cls, data: dict[str, Any]) -> Self:
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

    def with_modified(self, *, value: bool) -> "Skill":
        """Return a copy with the `modified` flag updated; raises if no upstream."""
        if self.mysk is None or not self.mysk.provenance.has_upstream:
            msg = "skill has no upstream; modified only applies to skills with a source"
            raise ValueError(msg)
        new_prov = self.mysk.provenance.model_copy(update={"modified": value})
        new_block = self.mysk.model_copy(update={"provenance": new_prov})
        return self.model_copy(update={"mysk": new_block})

    def with_state(self, state: LifecycleState) -> "Skill":
        """Return a copy with the lifecycle state updated; raises if no mysk block."""
        if self.mysk is None:
            msg = "skill has no mysk block; cannot set state"
            raise ValueError(msg)
        return self.model_copy(
            update={"mysk": self.mysk.model_copy(update={"state": state})}
        )

    def to_frontmatter(self) -> dict[str, Any]:
        """Render to a frontmatter dict with generic fields and the `mysk` block.

        An un-migrated skill emits no `mysk` key.
        """
        result: dict[str, Any] = {"name": self.name, "description": self.description}
        result.update(self.extra_fields)
        if self.mysk is not None:
            block: dict[str, Any] = {"state": self.mysk.state.value}
            if self.mysk.provenance.has_upstream:
                block["source"] = self.mysk.provenance.source
                block["modified"] = self.mysk.provenance.modified
                if self.mysk.provenance.upstream_name is not None:
                    block["upstream_name"] = self.mysk.provenance.upstream_name
            result["mysk"] = block
        return result
