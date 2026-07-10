"""Shared skill/target constants for the deploy tests.

Pure data builders with no `monkeypatch` involved, so they stay plain
module-level values rather than fixtures.
"""

from mysk.domain import LifecycleState
from tests.conftest import make_skill, make_target

_CLAUDE_TARGET = make_target("claude")
_CURSOR_TARGET = make_target("cursor")

_ACTIVE_SKILL = make_skill("foo", state=LifecycleState.ACTIVE)
_EXPERIMENTAL_SKILL = make_skill("bar", state=LifecycleState.EXPERIMENTAL)
_DEPRECATED_SKILL = make_skill("wip", state=LifecycleState.DEPRECATED)
