"""MyskBlock: the ownership block written into a skill's SKILL.md frontmatter."""

from pydantic import BaseModel, ConfigDict, Field

from mysk.domain.lifecycle import LifecycleState
from mysk.domain.provenance import Provenance


class MyskBlock(BaseModel):
    """The `mysk:` block — present only on skills owned by mysk.

    Its presence is the ownership signal (ADR-0001). When present it always
    carries a lifecycle `state` and, for imported skills, provenance. A skill
    with no block has yet to be migrated and is not represented here.
    """

    model_config = ConfigDict(frozen=True)

    state: LifecycleState
    provenance: Provenance = Field(default_factory=Provenance)
