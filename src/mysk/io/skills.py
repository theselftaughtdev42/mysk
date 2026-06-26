import os
from pathlib import Path

from platformdirs import user_data_dir
from pydantic import BaseModel, ConfigDict

from mysk.domain.skill import Skill
from mysk.io import frontmatter


def skill_library() -> Path:
    """Resolve the Skill Library directory, creating it if absent.

    Returns ``platformdirs.user_data_dir("mysk") / "skills"`` by default, or the
    ``MYSK_SKILLS_DIR`` path when that environment variable is set.
    """
    override = os.environ.get("MYSK_SKILLS_DIR")
    if override:
        library = Path(override).expanduser()
    else:
        library = Path(user_data_dir("mysk")) / "skills"
    library.mkdir(parents=True, exist_ok=True)
    return library


class SkillLoadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    skill: Skill | None
    schema_error: str | None


def load_skills(skills_root: Path) -> list[SkillLoadResult]:
    """Load every skill under ``skills_root``, sorted alphabetically by name.

    Each result carries the parsed ``Skill`` when the frontmatter is valid, or a
    ``schema_error`` string when the mysk block is absent or malformed.
    """
    results = []
    for path in sorted(skills_root.glob("*/SKILL.md")):
        data, _ = frontmatter.read(path.read_text())
        try:
            skill = Skill.from_frontmatter(data)
        except (ValueError, KeyError) as exc:
            results.append(
                SkillLoadResult(path=path, skill=None, schema_error=str(exc))
            )
            continue
        if skill.mysk is None:
            results.append(
                SkillLoadResult(
                    path=path,
                    skill=None,
                    schema_error="missing mysk block",
                )
            )
            continue
        results.append(SkillLoadResult(path=path, skill=skill, schema_error=None))
    return results


class CollisionError(Exception):
    pass


def check_collision(library: Path, name: str, source: str | None) -> None:
    """Raise CollisionError if *name* already exists in the Skill Library.

    Three cases:
    - Same name + same source  → suggest ``mysk refresh <name>``
    - Same name + different source → suggest ``--rename``
    - Same name + self-authored (no source) → suggest ``--rename``
    """
    skill_md = library / name / "SKILL.md"
    if not skill_md.exists():
        return

    data, _ = frontmatter.read(skill_md.read_text())
    try:
        existing = Skill.from_frontmatter(data)
    except (ValueError, KeyError) as exc:
        raise CollisionError(
            f"A skill named {name!r} already exists in the Skill Library but its "
            f"frontmatter is malformed. Resolve it manually before importing."
        ) from exc

    existing_source = (
        existing.mysk.provenance.source if existing.mysk is not None else None
    )

    if existing_source == source:
        raise CollisionError(
            f"A skill named {name!r} from the same source is already in the Skill "
            f"Library. To update it run: mysk refresh {name}"
        )

    raise CollisionError(f"A skill named {name!r} already exists in the Skill Library")
