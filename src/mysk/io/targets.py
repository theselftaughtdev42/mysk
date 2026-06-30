"""Deployment Target discovery and skill-presence checks."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from mysk.domain.skill import Skill
from mysk.io import frontmatter

_KNOWN: list[tuple[str, str]] = [
    ("claude", ".claude/skills"),
    ("cursor", ".cursor/skills"),
    ("codex", ".agents/skills"),
]


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


def is_deployed(target: Target, skill: Skill) -> bool:
    """Return True if *skill* has a mysk-owned entry at *target*."""
    skill_md = target.path / skill.name / "SKILL.md"
    if not skill_md.is_file():
        return False
    data, _ = frontmatter.read(skill_md.read_text())
    return "mysk" in data


def discover_targets(search_root: Path | None = None) -> list[Target]:
    """Return all known Deployment Targets whose parent directory exists."""
    root = search_root or Path.home()
    result = []
    for name, rel in _KNOWN:
        p = root / rel
        if p.parent.is_dir():
            result.append(Target(name=name, path=p))
    return result
