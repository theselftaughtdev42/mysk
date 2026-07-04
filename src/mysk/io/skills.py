"""Skill Library filesystem access: loading, collision checking, path resolution."""

import os
from dataclasses import dataclass
from pathlib import Path

from mysk.domain.mysk_block import MyskBlock
from mysk.domain.skill import Skill
from mysk.io import frontmatter


@dataclass(frozen=True)
class InstalledSkill:
    """A valid, mysk-owned skill installed at a known directory in the Skill Library."""

    skill: Skill
    mysk: MyskBlock
    dir: Path

    @property
    def skill_md(self) -> Path:
        """Path to this skill's SKILL.md entry point."""
        return self.dir / "SKILL.md"


@dataclass(frozen=True)
class SkillLoadError:
    """A SKILL.md that could not be loaded due to a missing or malformed mysk block."""

    path: Path
    schema_error: str


def _mysk_home() -> Path:
    """Resolve the mysk home directory: `$MYSK_HOME` or `~/.mysk` by default.

    A set `MYSK_HOME` has `~` expanded and any relative path resolved against
    the current working directory; an empty or unset value falls back to
    `~/.mysk`.
    """
    override = os.environ.get("MYSK_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".mysk"


def skill_library_path() -> Path:
    """Resolve the Skill Library path without creating it."""
    return _mysk_home() / "skills"


def skill_library() -> Path:
    """Resolve the Skill Library directory, creating it if absent.

    Returns `<mysk home>/skills`, where the mysk home is `~/.mysk` by default
    or the `MYSK_HOME` path when that environment variable is set.
    """
    library = skill_library_path()
    library.mkdir(parents=True, exist_ok=True)
    return library


def load_skills(
    skills_root: Path,
) -> tuple[list[InstalledSkill], list[SkillLoadError]]:
    """Load every skill under `skills_root`, sorted alphabetically by name.

    Returns a tuple of (installed, errors). Installed skills are valid and
    mysk-owned; errors carry the schema_error string for investigation.
    """
    installed: list[InstalledSkill] = []
    errors: list[SkillLoadError] = []
    for path in sorted(skills_root.glob("*/SKILL.md")):
        data, _ = frontmatter.read(path.read_text())
        try:
            skill = Skill.from_frontmatter(data)
        except (ValueError, KeyError) as exc:
            errors.append(SkillLoadError(path=path, schema_error=str(exc)))
            continue
        if skill.mysk is None:
            errors.append(SkillLoadError(path=path, schema_error="missing mysk block"))
            continue
        installed.append(InstalledSkill(skill=skill, mysk=skill.mysk, dir=path.parent))
    return installed, errors


class CollisionError(Exception):
    """Raised when a skill with the same name already exists in the Skill Library."""


def check_collision(library: Path, name: str, source: str | None) -> None:
    """Raise CollisionError if *name* already exists in the Skill Library.

    Three cases:
    - Same name + same source  → suggest `mysk refresh <name>`
    - Same name + different source → suggest `--rename`
    - Same name + self-authored (no source) → suggest `--rename`
    """
    # no skill by that name yet: no collision
    skill_md = library / name / "SKILL.md"
    if not skill_md.exists():
        return

    # load the colliding skill so its source can be compared
    data, _ = frontmatter.read(skill_md.read_text())
    try:
        existing = Skill.from_frontmatter(data)
    except (ValueError, KeyError) as exc:
        msg = (
            f"A skill named {name!r} already exists in the Skill Library but its "
            f"frontmatter is malformed. Resolve it manually before importing."
        )
        raise CollisionError(msg) from exc

    existing_source = (
        existing.mysk.provenance.source if existing.mysk is not None else None
    )

    # same source: the existing skill can be refreshed in place
    if existing_source == source:
        msg = (
            f"A skill named {name!r} from the same source is already in the Skill "
            f"Library. To update it run: mysk refresh {name}"
        )
        raise CollisionError(msg)

    msg = f"A skill named {name!r} already exists in the Skill Library"
    raise CollisionError(msg)
