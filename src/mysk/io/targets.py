"""Deployment Target discovery and skill-presence checks."""

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from mysk.domain.skill import Skill

_KNOWN: list[tuple[str, str]] = [
    ("claude", ".claude/skills"),
    ("cursor", ".cursor/skills"),
    ("codex", ".agents/skills"),
]


class UnknownAgentsError(Exception):
    """Raised when `--agents` names an agent outside the found target set."""

    def __init__(self, unknown: Sequence[str], available: Sequence[str]) -> None:
        """Record the *unknown* names and the *available* (found) target names."""
        self.unknown = list(unknown)
        self.available = list(available)
        super().__init__(
            f"Unknown agent(s): {', '.join(self.unknown)}. "
            f"Available: {', '.join(self.available)}"
        )


class Target(BaseModel):
    """A known Deployment Target: an agent's skills directory on the filesystem."""

    model_config = ConfigDict(frozen=True)

    name: str
    path: Path

    def label(self) -> str:
        """Return a human-readable label like `~/.claude/skills (claude)`."""
        try:
            display = "~/" + str(self.path.relative_to(Path.home()))
        except ValueError:
            display = str(self.path)
        return f"{display} ({self.name})"


def is_deployed(target: Target, skill: Skill, library: Path) -> bool:
    """Return True if *skill* has a mysk-owned symlink at *target*."""
    link = target.path / skill.name
    return link.is_symlink() and link.resolve().is_relative_to(library.resolve())


def discover_targets(search_root: Path | None = None) -> list[Target]:
    """Return all known Deployment Targets whose parent directory exists."""
    root = search_root or Path.home()
    result = []
    for name, rel in _KNOWN:
        p = root / rel
        if p.parent.is_dir():
            result.append(Target(name=name, path=p))
    return result


def narrow_targets(targets: Sequence[Target], agents: str | None) -> list[Target]:
    """Return *targets*, or the subset named by comma-separated *agents*.

    With no *agents*, every found target is returned — the all-found default.
    Otherwise the found set is narrowed to the named agents, preserving
    discovery order. A name outside the found set raises `UnknownAgentsError`
    carrying both the unknown names and the available (found) target names.
    """
    if agents is None:
        return list(targets)
    names = {n.strip() for n in agents.split(",")}
    found = {t.name for t in targets}
    unknown = names - found
    if unknown:
        raise UnknownAgentsError(sorted(unknown), [t.name for t in targets])
    return [t for t in targets if t.name in names]
